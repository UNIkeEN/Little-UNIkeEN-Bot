import mysql.connector
from utils.responseImage import *
from utils.basicEvent import send, warning
from utils.basicConfigs import BOT_SELF_QQ, ROOT_PATH
from typing import Union, Tuple, Any, List, Set
from utils.standardPlugin import StandardPlugin, CronStandardPlugin, NotPublishedException
from utils.configAPI import getPluginEnabledGroups
from threading import Timer, Semaphore
from datetime import datetime
import time
import os.path
import asyncio
from utils.sqlUtils import newSqlSession
try:
    from resources.api.mddApi import mddUrl, mddHeaders
except ImportError:
    raise NotPublishedException("mdd url and mdd headers are secret")

MDD_FILE_PATH = os.path.join(ROOT_PATH, 'data', str(BOT_SELF_QQ),  'mdd.json')
os.makedirs(os.path.join(ROOT_PATH, 'data', str(BOT_SELF_QQ), ), exist_ok=True)

def createMddRecordSql():
    mydb, mycursor = newSqlSession()
    mycursor.execute("""
    create table if not exists `mddRecord` (
        `seq` bigint unsigned not null auto_increment,
        `time` timestamp not null comment 'current time',
        `mode` bool not null comment '0 if close, 1 if open',
        `week` tinyint not null comment '0 to 6 from Monday to Sunday',
        primary key(`seq`)
    );""")

def recordMddStatus(mode:int, t: datetime):
    mydb, mycursor = newSqlSession()
    mycursor.execute("""
    insert into `mddRecord` (`time`, `mode`, `week`) values
    (%s, %s, %s)
    """, (t, mode, t.weekday()))

class SubscribeMdd(StandardPlugin):
    initGuard = Semaphore()
    # https://docs.python.org/3/faq/library.html#what-kinds-of-global-value-mutation-are-thread-safe
    subscribers = set()
    def __init__(self) -> None:
        if SubscribeMdd.initGuard.acquire(blocking=False):
            mydb, mycursor = newSqlSession()
            mycursor.execute("""
            create table if not exists `mddSubscriber`(
                `user_id` bigint not null,
                `subscribe_time` timestamp not null,
                primary key(`user_id`)
            );""")
            mycursor.execute("select `user_id` from `mddSubscriber`")
            for user_id, in list(mycursor):
                SubscribeMdd.subscribers.add(user_id)
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg in ['订阅麦当劳', '取消订阅麦当劳']
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        subscribe = msg == '订阅麦当劳'
        user_id = data['user_id']
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        mydb, mycursor = newSqlSession()
        try:
            if subscribe:
                if user_id in SubscribeMdd.subscribers:
                    send(target,"[CQ:reply,id=%d]订阅失败，您已订阅"%data['message_id'], data['message_type'])
                else:
                    SubscribeMdd.subscribers.add(user_id)
                    mycursor.execute("""
                    insert ignore into `mddSubscriber` (`user_id`, `subscribe_time`)
                    values (%d, from_unixtime(%d));"""%(
                        user_id,
                        data['time']
                    ))
                    send(target, "[CQ:reply,id=%d]订阅成功，注意添加bot好友接收通知信息"%data['message_id'], data['message_type'])
            else:
                if user_id not in SubscribeMdd.subscribers:
                    send(target,"[CQ:reply,id=%d]取消订阅失败，您尚未订阅"%data['message_id'], data['message_type'])
                else:
                    SubscribeMdd.subscribers.remove(user_id)
                    mycursor.execute("""
                    delete from `mddSubscriber` where `user_id` = %d
                    """%data['user_id'])
                    send(target,"[CQ:reply,id=%d]取消订阅成功"%data['message_id'], data['message_type'])
        except mysql.connector.Error as e:
            warning('mysql exception in SubscribeMdd: {}'.format(e))
            send(target,"[CQ:reply,id=%d]操作失败"%data['message_id'], data['message_type'])
        except BaseException as e:
            warning('base exception in SubscribeMdd: {}'.format(e))
            send(target,"[CQ:reply,id=%d]操作失败"%data['message_id'], data['message_type'])
        return "OK"
    def getPluginInfo(self) -> dict:
        return {
            'name': 'SubscribeMdd',
            'description': '麦当劳订阅',
            'commandDescription': '订阅麦当劳/取消订阅麦当劳',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': ['mddSubscriber'],
            'version': '1.0.3',
            'author': 'Teruteru',
        }
    @staticmethod
    def getMddSubscribers()->Set[int]:
        return SubscribeMdd.subscribers
    
class GetMddStatus(StandardPlugin):
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg == '-mdd'
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        req = getMddStatus()
        if req == None:
            send(target, '获取交大闵行麦当劳状态失败！', data['message_type'])
            return "OK"
        else:
            currentStatus = req
        if currentStatus :
            send(target, '交大闵行麦当劳当前状态：\n▶️营业中\n\n%s'%datetime.now().strftime("%Y-%m-%d %H:%M:%S"), data['message_type'])
        else:
            send(target, '交大闵行麦当劳当前状态：\n⏸️暂停营业\n\n%s'%datetime.now().strftime("%Y-%m-%d %H:%M:%S"), data['message_type'])
        return "OK"
        
    def getPluginInfo(self) -> dict:
        return {
            'name': 'GetMddStatus',
            'description': '麦当劳查询',
            'commandDescription': '-mdd',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.3',
            'author': 'Teruteru',
        }
        
class MonitorMddStatus(StandardPlugin, CronStandardPlugin):
    monitorSemaphore = Semaphore()
    @staticmethod
    def dumpMddStatus(status: bool):
        with open(MDD_FILE_PATH, 'w') as f:
            f.write('1' if status else '0')
    @staticmethod
    def loadMddStatus()->bool:
        with open(MDD_FILE_PATH, 'r') as f:
            return f.read().startswith('1')
    def __init__(self) -> None:
        self.exactPath = MDD_FILE_PATH
        self.prevStatus = False # false: 暂停营业, true: 营业
        if MonitorMddStatus.monitorSemaphore.acquire(blocking=False):
            createMddRecordSql()
            if not os.path.isfile(self.exactPath):
                MonitorMddStatus.dumpMddStatus(False)
            else:
                self.prevStatus = MonitorMddStatus.loadMddStatus()
            self.start(10, 30)

    def tick(self):
        req = getMddStatus()
        if req == None: return
        else: currentStatus = req
        recordMddStatus(currentStatus, datetime.now())
        if currentStatus != self.prevStatus:
            self.prevStatus = currentStatus
            MonitorMddStatus.dumpMddStatus(currentStatus)
            groupTasks = []
            if currentStatus :
                for group in getPluginEnabledGroups('mddmonitor'):
                    send(group, '📣交大闵行麦当劳 已▶️开放营业')
            else:
                for group in getPluginEnabledGroups('mddmonitor'):
                    send(group, '📣交大闵行麦当劳 已⏸️暂停营业')

    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return False
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        return "OK"
    def getPluginInfo(self) -> dict:
        return {
            'name': 'MonitorMddStatus',
            'description': '麦当劳状态监控',
            'commandDescription': 'None',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.3',
            'author': 'Teruteru',
        }
        
def getMddStatus()->Union[None, bool]:
    req = requests.get(mddUrl, headers=mddHeaders)
    if req.status_code != requests.codes.ok or not req.json()['success']:
        warning('mdd api failed!')
        return None
    else:
        try:
            return req.json()['data']['onlineBusinessStatus']
            for store in req.json()['data']['orderStoreItemList']:
                if store['beType'] == 1:
                    return store['orderStoreList'][0]['businessStatus']
        except BaseException as e:
            warning('mdd api failed!')
            return None
        