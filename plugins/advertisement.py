import os
import time
from threading import Semaphore
from typing import Any, Dict, List, Optional, Tuple, Union

from pymysql.converters import escape_string

from utils.basicConfigs import IMAGES_PATH, ROOT_PATH
from utils.basicEvent import get_group_msg_history, send, warning
from utils.configAPI import getPluginEnabledGroups
from utils.sqlUtils import newSqlSession
from utils.standardPlugin import CronStandardPlugin, StandardPlugin


def createAdvertisementSql():
    mydb, mycursor = newSqlSession()
    mycursor.execute("""
    create table if not exists `advertisementContext`(
        `group_id` bigint unsigned not null,
        `unique_key` char(64) not null,
        `last_message_seq` bigint,
        `last_time` timestamp,
        primary key(`group_id`, `unique_key`)
    )charset=utf8mb4, collate=utf8mb4_unicode_ci;""")

def getLatestSeqAndTime(group_id: int)->Optional[Tuple[int, int]]:
    currentTime = int(time.time())
    msgs = get_group_msg_history(group_id)
    if len(msgs) > 0:
        latestMsg = max(msgs, key=lambda x:x['message_seq'])
        return latestMsg['message_seq'], max(latestMsg['time'], currentTime)
    else:
        mydb, mycursor = newSqlSession()
        mycursor.execute("""
        select `message_seq`, unix_timestamp(`time`) from `messageRecord`
        where group_id = %d order by `message_seq` desc limit 1;
        """%(group_id, ))
        result = list(mycursor)
        if len(result) == 0:
            return None
        else:
            return result[0][0], max(result[0][1], currentTime)

class BaseAdvertisementClass(CronStandardPlugin):
    initGuard = Semaphore()
    def __init__(self, adword:str, group_id:int, uniqueKey:str, deltaTime:int, deltaMsg:int):
        """
        @group_id: 投放广告的目标群组
        @uniqueKey: 广告唯一标识（不同群可重合）
        @deltaTime: 广告最短间隔时间，单位 [second]
        @deltaMsg:  广告最短间隔消息条数，单位 [条]
        """
        if self.initGuard.acquire(blocking=False):
            createAdvertisementSql()
        assert isinstance(uniqueKey, str) and len(uniqueKey) < 64
        self.adword = adword
        self.group_id = group_id
        self.uniqueKey = uniqueKey
        self.deltaTime = deltaTime
        self.deltaMsg = deltaMsg
        lastMsgSeq, lastTime = self.loadContext()
        self.lastMsgSeq = lastMsgSeq
        self.lastTime = lastTime

        if lastMsgSeq == None or lastTime == None:
            lastMsgSeq, lastTime = getLatestSeqAndTime(self.group_id)
            self.dumpContext(lastMsgSeq, lastTime)

        self.job = self.start(0, 20) # check every 20s

    def tick(self):
        latestSeq, latestTime = getLatestSeqAndTime(self.group_id)
        # print(f'latestSeq: {latestSeq}, lastSeq: {self.lastMsgSeq}\nlatestTime: {latestTime}, lastTime: {self.lastTime}')
        if self.judgeSatisfy(latestSeq, latestTime):
            send(self.group_id, self.adword)
            self.dumpContext(latestSeq, latestTime)

    def loadContext(self)->Tuple[Optional[int], Optional[int]]:
        """
        @return: Tuple[last_message_seq, last_time]
        """
        mydb, mycursor = newSqlSession()
        mycursor.execute("""
        select `last_message_seq`, unix_timestamp(`last_time`) from `advertisementContext`
        where group_id = %d and unique_key = '%s'"""%(
            self.group_id, escape_string(self.uniqueKey)
        ))
        result = list(mycursor)
        if len(result) == 0:
            return None, None
        else:
            return result[0]

    def dumpContext(self, lastMsgSeq:int, lastTime:int):
        mydb, mycursor = newSqlSession()
        mycursor.execute("""replace into `advertisementContext`
        (`last_message_seq`,`last_time`,`group_id`, `unique_key`) 
        values (%d, from_unixtime(%d), %d, '%s')
        """%(
            lastMsgSeq, lastTime,
            self.group_id, escape_string(self.uniqueKey)
        ))
        self.lastMsgSeq = lastMsgSeq
        self.lastTime = lastTime

    def judgeSatisfy(self, latestSeq:int, latestTime:int):
        return (latestTime - self.lastTime >= self.deltaTime and 
                latestSeq - self.lastMsgSeq >= self.deltaMsg)
    
    def cancel(self):
        if self.job != None:
            self.job.remove()
            self.job = None
    def isValid(self):
        return self.job != None
    def __del__(self):
        self.cancel()
class McAdManager(StandardPlugin):
    def __init__(self):
        self.groups = {}
        # self.adword = (
        #     "点我体验交大mc生活，一起来Minecraft社建设方块交大，"
        #     "体验原汁原味的原版生存，享受多汁多彩的模组世界，"
        #     "我们欢迎热爱MC的各位玩家，加入我们的世界712514518"
        #     f"[CQ:image,file=file:///{os.path.join(ROOT_PATH, IMAGES_PATH, 'mc.png')}]"
        #     "进群看学长女装~"
        # )
        self.adword = (
            '问 mc'
        )
        self.uniqueKey = 'sjmcad'
        # self.deltaTime = 0 # 40 min
        # self.deltaMsg = 0  # 100 msg 
        self.deltaTime = 60 * 60 # 60 min
        self.deltaMsg = 150      #150 msg 
        for group_id in getPluginEnabledGroups('mcad'):
            self.groups[group_id] = BaseAdvertisementClass(self.adword, group_id, self.uniqueKey, self.deltaTime, self.deltaMsg)

    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return False
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        return None
    def getPluginInfo(self) -> dict:
        return {
            'name': 'McAdManager',
            'description': 'MC广告播报',
            'commandDescription': '[-grpcfg驱动]',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }

    def onStateChange(self, nextState: bool, data: Any) -> None:
        group_id = data['group_id']
        if nextState:
            self.groups[group_id] = BaseAdvertisementClass(self.adword, group_id, self.uniqueKey, self.deltaTime, self.deltaMsg)
        else:
            if group_id in self.groups.keys():
                self.groups[group_id].cancel()
                del self.groups[group_id]