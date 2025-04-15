import asyncio
import base64
import copy
import datetime
import os
import random
import re
import time
from io import BytesIO
from threading import Semaphore, Thread
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from PIL import Image

from utils.basicConfigs import APPLY_GROUP_ID, ROOT_PATH, SAVE_TMP_PATH
from utils.basicEvent import gocqQuote, send, warning
from utils.sqlUtils import newSqlSession
from utils.standardPlugin import CronStandardPlugin, Job, StandardPlugin

from .core.user import RelationType, User, get_self_info
from .core.w_webid import get_w_webid
from .core.wbi import getWbiKeys
from .painter.DynamicPicGenerator import DynamicPicGenerator
from .starbot_utils.config import set_credential
from .starbot_utils.network import request
from .starbot_utils.utils import get_credential


def get_bilibili_user_info(loop, uid:int, wbi_keys: Dict[str, str], w_webid: str)->Dict:
    user = User(uid, get_credential(), wbi_keys=wbi_keys, w_webid = w_webid)
    return loop.run_until_complete(loop.create_task(user.get_user_info_wbi()))

def get_bilibili_user_name(loop, uid:int, wbi_keys: Dict[str, str], w_webid: str)->Optional[str]:
    try:
        info = get_bilibili_user_info(loop, uid, wbi_keys, w_webid)
        name = info['name']
        return name
    except Exception as e:
        return None

async def subscribe_bilibili_users(uids:List[int], relationType: RelationType=RelationType.SUBSCRIBE) -> None:
    for uid in uids:
        user = User(uid, get_credential())
        result = await user.modify_relation(relationType)
        await asyncio.sleep(12)

def get_dynamic_desc(event)->Tuple[str, str]:
    """
    动态更新事件
    """
    dynamic_id = event["desc"]["dynamic_id"]
    dynamic_type = event["desc"]["type"]
    bvid = event['desc']['bvid'] if dynamic_type == 8 else ""
    rid = event['desc']['rid'] if dynamic_type in (64, 256) else ""

    action_map = {
        1: "转发了动态",
        2: "发表了新动态",
        4: "发表了新动态",
        8: "投稿了新视频",
        64: "投稿了新专栏",
        256: "投稿了新音频",
        2048: "发表了新动态"
    }
    url_map = {
        1: f"https://t.bilibili.com/{dynamic_id}",
        2: f"https://t.bilibili.com/{dynamic_id}",
        4: f"https://t.bilibili.com/{dynamic_id}",
        8: f"https://www.bilibili.com/video/{bvid}",
        64: f"https://www.bilibili.com/read/cv{rid}",
        256: f"https://www.bilibili.com/audio/au{rid}",
        2048: f"https://t.bilibili.com/{dynamic_id}"
    }
    action = action_map.get(dynamic_type, "发表了新动态")
    url = url_map.get(dynamic_type, 'https://www.bilibili.com/opus/' + str(dynamic_id))
    return action, url

class BilibiliSubscribeHelper(StandardPlugin):
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg in ["B站订阅帮助", "b站订阅帮助", '订阅帮助'] and data['message_type']=='group'
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        group_id = data['group_id']
        send(group_id,'订阅帮助: 订阅帮助 / B站订阅帮助\n' 
                    '订阅up:    订阅 <uid>\n'
                    '取消订阅: 取消订阅 <uid>\n'
                    '获取订阅列表: 订阅\n'
                    '注意:  关闭本插件会自动取消所有已订阅的up')
        return "OK"
    def getPluginInfo(self) -> dict:
        return {
            'name': 'BilibiliSubscribeHelper',
            'description': 'B站订阅帮助',
            'commandDescription': '订阅帮助',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
        
def createBilibiliTable()->None:
    mydb, mycursor = newSqlSession()
    mycursor.execute("""
    create table if not exists `bilibiliDynamic` (
        `uid` bigint unsigned not null,
        `dynamicId` bigint unsigned not null,
        `uploadTime` timestamp not null,
        primary key (`uid`)
    )""")
    mycursor.execute("""
    create table if not exists `bilibiliSubscribe` (
        `group_id` bigint unsigned not null,
        `uid` bigint unsigned not null,
        primary key(`group_id`, `uid`)
    )""")
    mycursor.execute("""
    create table if not exists `bilibiliNickCache` (
        `uid` bigint unsigned not null,
        `nickname` varchar(100) not null,
        primary key(`uid`)
    )charset=utf8mb4, collate=utf8mb4_unicode_ci;""")

def loadPrevMetas(uids: List[int])->List[Optional[Tuple[int, int]]]:
    mydb, mycursor = newSqlSession()
    mycursor.executemany("""select `uid`, `dynamicId`, unix_timestamp(`uploadTime`) 
                         from `bilibiliDynamic` where `uid` = %s""", 
                         [(uid, ) for uid in uids])
    results = mycursor.fetchall()
    metas = [None] * len(uids)
    for uid, dynamicId, uploadTime in results:
        index = uids.index(uid)
        metas[index] = (uploadTime, dynamicId)
    return metas

def getCachedNick(uid: int)->Optional[str]:
    mydb, mycursor = newSqlSession()
    mycursor.execute("""select `nickname` from `bilibiliNickCache`
                     where `uid` = %s""", (uid, ))
    results = list(mycursor)
    if len(results) == 0:
        return None
    return results[0][0]

def getCachedNicks(uids: List[int])->List[Optional[str]]:
    mydb, mycursor = newSqlSession()
    mycursor.executemany("""select `uid`, `nickname` from `bilibiliNickCache`
                     where `uid` = %s""", [(uid, ) for uid in uids])
    results = mycursor.fetchall()
    nicks = [None] * len(uids)
    for uid, nick in results:
        index = uids.index(uid)
        nicks[index] = nick
    return nicks

def updateNickCache(uid:int, nickname:str)->None:
    mydb, mycursor = newSqlSession()
    mycursor.execute("""replace into `bilibiliNickCache`
                     (`uid`, `nickname`) values (%s, %s)""", (uid, nickname))

def updateNickCaches(uids:List[int], nicknames:List[str])->None:
    mydb, mycursor = newSqlSession()
    mycursor.executemany("""replace into `bilibiliNickCache`
                     (`uid`, `nickname`) values (%s, %s)""", list(zip(uids, nicknames)))

class BilibiliSubscribe(StandardPlugin, CronStandardPlugin):
    initGuard = Semaphore()
    def __init__(self, credential: Dict[str, str]) -> None:
        """
        self.bUps: uid -> UserFixed
        self.groupUps: group_id -> Set[uid: int]
        """
        if self.initGuard.acquire(blocking=False):
            createBilibiliTable()
        self.loop = asyncio.new_event_loop()
        self.pattern1 = re.compile(r'^订阅\s*(\d+)$')
        self.pattern2 = re.compile(r'^取消订阅\s*(\d+)$')
        self.pattern3 = re.compile(r'^订阅$')
        # 维护以下两个数组
        self.groupToUps:Dict[int, Set[int]] = {}
        self.upToGroups:Dict[int, Set[int]] = {}
        self.wbiKeys:Dict[str, str] = None
        self.w_webid:str = None
        self.wbiKeyDate:datetime.date = None    
        self._prevMeta: Dict[int, Optional[Tuple[int, int]]] = {}
        self._loadFromSql()
        
        set_credential(sessdata=credential.get('sessdata', ''),
                       bili_jct=credential.get('bili_jct', ''),
                       buvid3=credential.get('buvid3', ''))
        self._selfUid:Optional[int] = None
        self.updateWbiKeys()
        self.subscribeWatchings()
        self.job = self.start(0, 60)
        
    def getSelfSubscribes(self) -> List[int]:
        user = User(self.getSelfUid(), get_credential())
        loop = self.loop
        selfFollowing = loop.run_until_complete(loop.create_task(user.get_followings()))
        uids, unames = [], []
        for follow in selfFollowing.get('list', []):
            uids.append(int(follow.get('mid')))
            unames.append(follow.get('uname'))
        updateNickCaches(uids, unames)
        return uids
    
    def subscribeWatchings(self, block:bool = False) -> None:
        # 1. get todo list
        subscribed = self.getSelfSubscribes()
        uids = []
        for uid, groups in self.upToGroups.items():
            if len(groups) == 0: continue
            if uid in subscribed: continue
            uids.append(uid)
        # 2. subscribe
        if block:
            loop = self.loop
            loop.run_until_complete(loop.create_task(subscribe_bilibili_users(uids)))
        else:
            asyncio.run_coroutine_threadsafe(subscribe_bilibili_users(uids), self.loop)
        # 3. ubsubscribe   
        uids = []
        for uid in subscribed:
            if uid in self.upToGroups.keys(): 
                if len(self.upToGroups[uid]) != 0:
                    continue
            uids.append(uid)
        if block:
            loop = self.loop
            loop.run_until_complete(loop.create_task(subscribe_bilibili_users(uids, RelationType.UNSUBSCRIBE)))
        else:
            asyncio.run_coroutine_threadsafe(subscribe_bilibili_users(uids, RelationType.UNSUBSCRIBE), self.loop)
            
    def getSelfUid(self) -> int:
        if self._selfUid != None:
            return self._selfUid
        loop = self.loop
        result = loop.run_until_complete(loop.create_task(get_self_info(get_credential())))
        self._selfUid = result.get('mid', None)
        return self._selfUid
    
    def updateWbiKeys(self) -> None:
        today = datetime.date.today()
        if self.wbiKeyDate != None and today == self.wbiKeyDate:
            return
        self.wbiKeyDate = today
        img_key, sub_key = getWbiKeys()
        self.wbiKeys = {
            'img_key': img_key,
            'sub_key': sub_key
        }
        self.w_webid = get_w_webid(self.getSelfUid())
        
    def _loadFromSql(self)->None:
        mydb, mycursor = newSqlSession()
        mycursor.execute("""
        select `group_id`, `uid` from `bilibiliSubscribe`
        """)
        uids = []
        for group_id, uid in list(mycursor):
            if group_id not in APPLY_GROUP_ID: continue
            if group_id not in self.groupToUps.keys():
                self.groupToUps[group_id] = set()
            if uid not in self.upToGroups.keys():
                self.upToGroups[uid] = set()
            self.groupToUps[group_id].add(uid)
            self.upToGroups[uid].add(group_id)
            uids.append(uid)
        prevMetas = loadPrevMetas(uids)
        for uid, prevMeta in zip(uids, prevMetas):
            self._prevMeta[uid] = prevMeta
    
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return self.pattern1.match(msg) != None or\
               self.pattern2.match(msg) != None or\
               self.pattern3.match(msg) != None 

    def subscribeBilibili(self, group_id:int, bilibili_uid:int)->None:
        if group_id not in self.groupToUps.keys():
            self.groupToUps[group_id] = set()

        if bilibili_uid not in self.upToGroups.keys():
            self.upToGroups[bilibili_uid] = set()
            loop = self.loop
            if bilibili_uid not in self.upToGroups.keys():
                try:
                    user = User(bilibili_uid, get_credential())
                    loop.run_until_complete(loop.create_task(user.modify_relation(RelationType.SUBSCRIBE)))
                except Exception as e:
                    warning('exception in subscribeBilibili: {}'.format(e))
        if bilibili_uid not in self.groupToUps[group_id]:
            self.groupToUps[group_id].add(bilibili_uid)
            self.upToGroups[bilibili_uid].add(group_id)
            mydb, mycursor = newSqlSession()
            mycursor.execute("""
            insert ignore into `bilibiliSubscribe` set
            group_id = %d,
            uid = %d
            """%(group_id, bilibili_uid))
            
    def unsubscribeBilibili(self, group_id:int, bilibili_uid:int)->None:
        if bilibili_uid not in self.groupToUps.get(group_id, set()): return
        self.groupToUps.get(group_id, set()).discard(bilibili_uid)
        self.upToGroups.get(bilibili_uid, set()).discard(group_id)
        mydb, mycursor = newSqlSession()
        mycursor.execute("""
        delete from `bilibiliSubscribe` where
        group_id = %d and
        uid = %d
        """%(group_id, bilibili_uid))

    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        group_id = data['group_id']
        if self.pattern1.match(msg) != None:
            uid = self.pattern1.findall(msg)[0]
            uid = int(uid)
            if len(self.groupToUps.get(group_id, [])) >= 10:
                send(group_id, f'[CQ:reply,id={data["message_id"]}]订阅失败，当前群内订阅UP主过多')
            else:
                userName = getCachedNick(uid)
                if userName == None:
                    userName = get_bilibili_user_name(self.loop, uid, self.wbiKeys, self.w_webid)
                    if userName != None:
                        updateNickCache(uid, userName)
                if userName != None:
                    self.subscribeBilibili(group_id, uid)
                    name = gocqQuote(userName)
                    send(group_id, f'[CQ:reply,id={data["message_id"]}]订阅成功！\nname: {name}\nuid: {uid}')
                else:
                    send(group_id, f'[CQ:reply,id={data["message_id"]}]订阅失败，用户名称查询出错')
        elif self.pattern2.match(msg) != None:
            uid = self.pattern2.findall(msg)[0]
            uid = int(uid)
            if uid in self.groupToUps.get(group_id, []):
                self.unsubscribeBilibili(group_id, uid)
                nick = getCachedNick(uid)
                if nick == None:
                    nick = '【未知昵称】'
                send(group_id, '[CQ:reply,id=%d]已取消订阅 %s'%(data['message_id'], nick))
            else:
                send(group_id, '[CQ:reply,id=%d]未订阅该UP主'%data['message_id'])
                
        elif self.pattern3.match(msg) != None:
            ups = self.groupToUps.get(group_id, set())
            if len(ups) == 0:
                send(group_id, '[CQ:reply,id=%d]本群还没有订阅up哦~'%data['message_id'])
            else:
                ups = sorted(list(ups))
                nicks = getCachedNicks(ups)
                for i, (up, nick) in enumerate(zip(ups, nicks)):
                    if nick is None:
                        nick = get_bilibili_user_name(self.loop, up, self.wbiKeys, self.w_webid)
                        if nick == None:
                            nick = '【获取用户名失败】'
                        else:
                            updateNickCache(up, nick)
                        nicks[i] = nick
                metas = [f"name: {nick}\nuid: {uid}" for nick, uid in zip(nicks, ups)]
                send(group_id,f'本群订阅的up有：\n\n'+'\n----------\n'.join(metas))
        else:
            pass
            
        return "OK"
    
    def onStateChange(self, nextState: bool, data: Any) -> None:
        group_id = data['group_id']
        if nextState or group_id not in self.groupToUps.keys(): return
        for uid in copy.deepcopy(self.groupToUps[group_id]):
            self.unsubscribeBilibili(group_id, uid)

    def getPluginInfo(self) -> dict:
        return {
            'name': 'BilibiliSubscribe',
            'description': '订阅B站up',
            'commandDescription': '订阅/订阅 <uid>/取消订阅 <uid>',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
        
    def checkUpdate(self, detail:Dict) -> bool:
        try:
            uid:int = detail['desc']['uid']
            dynamic_id:int = detail['desc']['dynamic_id']
            timestamp = detail['desc']['timestamp']
            prevMeta = self.getPrevMeta(uid)
            if prevMeta != None and (prevMeta[0] >= timestamp or prevMeta[1] == dynamic_id):
                return False
            self.writeMeta(uid, timestamp, dynamic_id)
            return True
        except:
            return False
        
    def getPrevMeta(self, uid: int)->Optional[Tuple[int, int]]:
        """获取该up主记录在册的前一次上传数据
        @return: Optional[(
            [0]: int: uploadTime unix时间戳
            [1]: str: dynamic_id
        )]
        """
        if self._prevMeta.get(uid, None) == None:
            mydb, mycursor = newSqlSession()
            mycursor.execute("""
            select unix_timestamp(`uploadTime`), `dynamicId` from `bilibiliDynamic` where
            uid = %d
            """%uid)
            meta = list(mycursor)
            if len(meta) != 0:
                self._prevMeta[uid] = meta[0]
        return self._prevMeta[uid]
        
    def writeMeta(self, uid:int, uploadTime:int, dynamicId:int)->None:
        """写入up主本次上传数据"""
        meta = (uploadTime, dynamicId)
        self._prevMeta[uid] = meta
        mydb, mycursor = newSqlSession()
        # print(uploadTime, dynamicId, uid)
        mycursor.execute("""
        replace into `bilibiliDynamic` set
        uploadTime = from_unixtime(%s),
        dynamicId = %s,
        uid = %s
        """, (uploadTime, dynamicId, uid))
    
    def tick(self):
        print('[TICK] bilibili update')
        self.updateWbiKeys()
        async def check_bilibili():
            dynamic_url = "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/dynamic_new?type_list=268435455"
            credential = get_credential()
            latest_dynamic = await request('GET', url=dynamic_url, credential=credential)
            for detail in latest_dynamic["cards"]:
                uid = detail.get('desc', {}).get('uid', None)
                dynamicId = detail.get('desc', {}).get('dynamic_id', None)
                uname = detail['desc']['user_profile']['info']['uname']
                updateNickCache(uid, uname)
                if self.checkUpdate(detail):
                    base64str = await DynamicPicGenerator.generate(detail)
                    img = Image.open(BytesIO(base64.b64decode(base64str)))
                    imgPath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'biliDynamic-%d.png'%dynamicId)
                    img.save(imgPath)
                    action, url = get_dynamic_desc(detail)
                    for groupId in self.upToGroups.get(uid, []):
                        send(groupId, f'本群订阅UP主 【{uname}】 {action}\n\n链接：{url}')
                        send(groupId, f'[CQ:image,file=file:///{imgPath}]')
        loop = self.loop
        loop.run_until_complete(loop.create_task(check_bilibili()))

    def checkSelfStatus(self):
        self.tick()
        return 1, 1, '正常'
    