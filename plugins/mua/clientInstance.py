import asyncio
import datetime
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from utils.responseImage_beta import *
from utils.sqlUtils import newSqlSession
from utils.standardPlugin import NotPublishedException

from .client import Client
from .common.subprotocols import (Announcement, CreateAnnouncementPacket,
                                  DeleteAnnouncementPacket,
                                  QueryAnnouncementListPacket)

try:
    from resources.api.muaID import BOT_MUA_ID, BOT_MUA_TOKEN, MUA_URL
except ImportError as e:
    BOT_MUA_ID, BOT_MUA_TOKEN, MUA_URL = None, None, None
    # raise NotPublishedException('BOT MUA ID缺失，无法使用mua插件')
muaClientInstance = Client(BOT_MUA_ID, BOT_MUA_TOKEN, MUA_URL)
muaClientInstanceRunning = False

def setMuaCredential(BOT_MUA_ID:str, BOT_MUA_TOKEN:str, MUA_URL:str):
    muaClientInstance.reset_credential(BOT_MUA_ID, BOT_MUA_TOKEN, MUA_URL)

def createMuaSessionIdSql():
    mydb, mycursor = newSqlSession()
    mycursor.execute("""
    create table if not exists `muaSessionId` (
        `session_id` char(40) not null comment 'MUA会话uuid',
        `user_id` bigint unsigned comment 'QQ会话用户',
        `target` bigint unsigned comment 'QQ会话对象(群组或用户)',
        `message_type` char(20) comment 'QQ会话对象类型',
        `time` char(20) comment 'QQ会话时间',
        `message_id` bigint comment 'QQ消息id',
        `ann_key` char(64) comment 'announce标识主键',
        `abstract` bool default false comment '是否查询mua通知摘要',
        primary key(`session_id`)
    );""")

def dumpMuaSession(sessionId:str, data:Any, annKey:str, abstract:bool=False):
    """将Mua会话保存到sql，以便收到返回payload包时恢复会话
    @sessionId: 会话id
    @data:      gocqhttp的data，包含time、message_id、user_id、message_type等
    @annKey:    用户的announcement关键字
    @abstract:  是否以摘要形式发送（用于处理用户查询返回的LIST）
    """
    target = data['group_id'] if data['message_type']=='group' else data['user_id']
    mydb, mycursor = newSqlSession()
    mycursor.execute("""
    replace into `muaSessionId`
    (`session_id`, `user_id`, `target`, `message_type`, `time`, `message_id`, `ann_key`, `abstract`) values
    (%s, %s, %s, %s, %s, %s, %s, %s)
    """,(sessionId, data['user_id'], target, data['message_type'], data['time'],
        data['message_id'], annKey, abstract))

def loadMuaSession(sessionId:str)->Optional[Any]:
    """根据sessionId恢复MUA会话
    @sessionId: sessionId
    """
    mydb, mycursor = newSqlSession()
    mycursor.execute("""
    select `user_id`, `target`, `message_type`, `time`, `message_id`, `ann_key`, `abstract` from
    `muaSessionId` where `session_id` = %s
    """, (sessionId,))
    result = list(mycursor)
    if len(result) == 0: return None
    userId, target, messageType, t, messageId, annKey, abstract = result[0]
    return {
        'user_id': userId,
        'target': target,
        'message_type': messageType,
        'time': t,
        'message_id': messageId,
        'ann_key': annKey,
        'abstract': abstract,
    }

def clientInstanceMainloop():
    """client实例的主循环"""
    async def mainloop():
        global muaClientInstanceRunning
        await muaClientInstance.connect()
        await muaClientInstance.authenticate()
        muaClientInstanceRunning = True
        print('MUA SERVER OK')
        await muaClientInstance.event_loop()
        muaClientInstanceRunning = False
    while True:
        try:
            asyncio.run(mainloop())
        except Exception as e:
            print('[ERROR]: MUA session error:', e)
            time.sleep(3)
        print('!!!!MUA SESSIONLOST')
        time.sleep(1)

__instanceStarted = False
__muaClientInstanceMainloop = threading.Thread(target=clientInstanceMainloop)
__muaClientInstanceMainloop.daemon = True
def startMuaInstanceMainloop():
    global __instanceStarted
    if not __instanceStarted:
        __instanceStarted = True
        __muaClientInstanceMainloop.start()
    else:
        print("[WARNING]: mua mainloop instance already started")
    
def sendAnnouncement(announcement:Announcement, data:Any, annKey:str)->Tuple[bool, str]:
    """向MUA服务器发送announcement
    @announcement: 待发送的announcement
    @data:         gocqhttp的data包
    @annKey:       announce的用户关键字

    @return:       Tuple[是否成功, 描述]
    """
    global muaClientInstanceRunning, muaClientInstance
    if muaClientInstanceRunning:
        sessionId = str(uuid.uuid4())
        dumpMuaSession(sessionId, data, annKey)
        packet = CreateAnnouncementPacket(announcement, session_id=sessionId)
        asyncio.run(muaClientInstance.send_payload(packet))
        return True, '发送成功，等待mua服务器反馈'
    return False, '发送失败，与mua服务器断开连接'

def deleteAnnouncement(aid:int, author_token:str)->Tuple[bool, str]:
    global muaClientInstanceRunning, muaClientInstance
    if muaClientInstanceRunning:
        packet = DeleteAnnouncementPacket(aid=aid, author_token=author_token)
        asyncio.run(muaClientInstance.send_payload(packet))
        return True, '发送成功，等待mua服务器反馈'
    return False, '删除失败，与mua服务器断开连接'

def queryAnnouncement(data:Any, abstract:bool=False)->Tuple[bool, str]:
    global muaClientInstanceRunning, muaClientInstance
    if muaClientInstanceRunning:
        sessionId = str(uuid.uuid4())
        dumpMuaSession(sessionId, data, None, abstract=abstract)
        packet = QueryAnnouncementListPacket(sessionId)
        asyncio.run(muaClientInstance.send_payload(packet))
        return True, '查询指令发送成功，等待mua服务器反馈'
    return False, '查询指令发送失败，与mua服务器断开连接'

if True:
    if BOT_MUA_ID != None and BOT_MUA_TOKEN != None and MUA_URL != None:
        startMuaInstanceMainloop()