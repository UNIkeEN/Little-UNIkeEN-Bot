from .client import Client 
import asyncio
import threading
from utils.standardPlugin import NotPublishedException
from utils.basicEvent import send
from .common.subprotocols import Announcement, CreateAnnouncementPacket
import uuid
from utils.basicConfigs import sqlConfig
import mysql.connector
from typing import Any, Optional
import time
try:
    from resources.api.muaID import BOT_MUA_ID, BOT_MUA_TOKEN, MUA_URL
except ImportError as e:
    raise NotPublishedException('BOT MUA ID缺失，无法使用mua插件')
muaClientInstance = Client(BOT_MUA_ID, BOT_MUA_TOKEN, MUA_URL)
muaClientInstanceRunning = False



def createMuaSessionIdSql():
    mydb = mysql.connector.connect(**sqlConfig)
    mydb.autocommit = True
    mycursor = mydb.cursor()
    mycursor.execute("""
    create table if not exists `BOT_DATA`.`muaSessionId` (
        `session_id` char(40) not null comment 'MUA会话uuid',
        `user_id` bigint unsigned comment 'QQ会话用户',
        `target` bigint unsigned comment 'QQ会话对象(群组或用户)',
        `message_type` char(20) comment 'QQ会话对象类型',
        `time` char(20) comment 'QQ会话时间',
        primary key(`session_id`)
    );""")
createMuaSessionIdSql()

def dumpMuaSession(sessionId:str, data:Any):
    target = data['group_id'] if data['message_type']=='group' else data['user_id']
    mydb = mysql.connector.connect(**sqlConfig)
    mydb.autocommit = True
    mycursor = mydb.cursor()
    mycursor.execute("""
    replace into `BOT_DATA`.`muaSessionId`
    (`session_id`, `user_id`, `target`, `message_type`, `time`) values
    (%s, %s, %s, %s, %s)
    """,(sessionId, data['user_id'], target, data['message_type'], data['time']))

def loadMuaSession(sessionId:str)->Optional[Any]:
    mydb = mysql.connector.connect(**sqlConfig)
    mydb.autocommit = True
    mycursor = mydb.cursor()
    mycursor.execute("""
    select `user_id`, `target`, `message_type`, `time` from
    `BOT_DATA`.`muaSessionId` where `session_id` = %s
    """, (sessionId,))
    result = list(mycursor)
    if len(result) == 0: return None
    userId, target, messageType, t = result[0]
    return {
        'user_id': userId,
        'target': target,
        'message_type': message_type,
        'time': t
    }

def handle_payload_fn(session_id, payload):
    data = loadMuaSession(session_id)
    if data != None:
        send(data['target'], payload.serialize_content(), data['message_type'])
muaClientInstance.set_handle_payload_fn(handle_payload_fn)

def clientInstanceMainloop():
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
__muaClientInstanceMainloop = threading.Thread(target=clientInstanceMainloop)
__muaClientInstanceMainloop.start()


def sendAnnouncement(announcement:Announcement, data:Any)->bool:
    global muaClientInstanceRunning, muaClientInstance
    if muaClientInstanceRunning:
        sessionId = str(uuid.uuid4())
        dumpMuaSession(sessionId, data)
        packet = CreateAnnouncementPacket(announcement, session_id=sessionId)
        asyncio.run(muaClientInstance.send_payload(packet))
        return True
    return False
