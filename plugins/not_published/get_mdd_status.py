import mysql.connector
from utils.response_image import *
from utils.basic_event import send, warning, aio_send
from typing import Union, Tuple, Any, List, Set
from utils.standard_plugin import StandardPlugin, CronStandardPlugin, NotPublishedException
from utils.config_api import get_plugin_enabled_groups
from threading import Timer, Semaphore
from datetime import datetime
import time
import os.path
import asyncio
from utils.sql_utils import new_sql_session

try:
    from resources.api.mddApi import mddUrl, mddHeaders
except ImportError:
    raise NotPublishedException("mdd url and mdd headers are secret")


def create_mdd_record_sql():
    mydb, mycursor = new_sql_session()
    mycursor.execute("""
    create table if not exists `mddRecord` (
        `seq` bigint unsigned not null auto_increment,
        `time` timestamp not null comment 'current time',
        `mode` bool not null comment '0 if close, 1 if open',
        `week` tinyint not null comment '0 to 6 from Monday to Sunday',
        primary key(`seq`)
    );""")


def record_mdd_status(mode: int, t: datetime):
    mydb, mycursor = new_sql_session()
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
            mydb, mycursor = new_sql_session()
            mycursor.execute("""
            create table if not exists `mddSubscriber`(
                `user_id` bigint not null,
                `subscribe_time` timestamp not null,
                primary key(`user_id`)
            );""")
            mycursor.execute("select `user_id` from `mddSubscriber`")
            for user_id, in list(mycursor):
                SubscribeMdd.subscribers.add(user_id)

    def judge_trigger(self, msg: str, data: Any) -> bool:
        return msg in ['订阅麦当劳', '取消订阅麦当劳']

    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        subscribe = msg == '订阅麦当劳'
        user_id = data['user_id']
        target = data['group_id'] if data['message_type'] == 'group' else data['user_id']
        mydb, mycursor = new_sql_session()
        try:
            if subscribe:
                if user_id in SubscribeMdd.subscribers:
                    send(target, "[CQ:reply,id=%d]订阅失败，您已订阅" % data['message_id'], data['message_type'])
                else:
                    SubscribeMdd.subscribers.add(user_id)
                    mycursor.execute("""
                    insert ignore into `mddSubscriber` (`user_id`, `subscribe_time`)
                    values (%d, from_unixtime(%d));""" % (
                        user_id,
                        data['time']
                    ))
                    send(target, "[CQ:reply,id=%d]订阅成功，注意添加bot好友接收通知信息" % data['message_id'],
                         data['message_type'])
            else:
                if user_id not in SubscribeMdd.subscribers:
                    send(target, "[CQ:reply,id=%d]取消订阅失败，您尚未订阅" % data['message_id'], data['message_type'])
                else:
                    SubscribeMdd.subscribers.remove(user_id)
                    mycursor.execute("""
                    delete from `mddSubscriber` where `user_id` = %d
                    """ % data['user_id'])
                    send(target, "[CQ:reply,id=%d]取消订阅成功" % data['message_id'], data['message_type'])
        except mysql.connector.Error as e:
            warning('mysql exception in SubscribeMdd: {}'.format(e))
            send(target, "[CQ:reply,id=%d]操作失败" % data['message_id'], data['message_type'])
        except BaseException as e:
            warning('base exception in SubscribeMdd: {}'.format(e))
            send(target, "[CQ:reply,id=%d]操作失败" % data['message_id'], data['message_type'])
        return "OK"

    def get_plugin_info(self) -> dict:
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
    def get_mdd_subscribers() -> Set[int]:
        return SubscribeMdd.subscribers


class GetMddStatus(StandardPlugin):
    def judge_trigger(self, msg: str, data: Any) -> bool:
        return msg == '-mdd'

    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type'] == 'group' else data['user_id']
        req = get_mdd_status()
        if req == None:
            send(target, '获取交大闵行麦当劳状态失败！', data['message_type'])
            return "OK"
        else:
            currentStatus = req
        if currentStatus:
            send(target, '交大闵行麦当劳当前状态：\n▶️营业中\n\n%s' % datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                 data['message_type'])
        else:
            send(target, '交大闵行麦当劳当前状态：\n⏸️暂停营业\n\n%s' % datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                 data['message_type'])
        return "OK"

    def get_plugin_info(self) -> dict:
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
    def dump_mdd_status(status: bool):
        exactPath = 'data/mdd.json'
        with open(exactPath, 'w') as f:
            f.write('1' if status else '0')

    @staticmethod
    def load_mdd_status() -> bool:
        exactPath = 'data/mdd.json'
        with open(exactPath, 'r') as f:
            return f.read().startswith('1')

    def __init__(self) -> None:
        self.exactPath = 'data/mdd.json'
        self.prevStatus = False  # false: 暂停营业, true: 营业
        if MonitorMddStatus.monitorSemaphore.acquire(blocking=False):
            create_mdd_record_sql()
            if not os.path.isfile(self.exactPath):
                MonitorMddStatus.dump_mdd_status(False)
            else:
                self.prevStatus = MonitorMddStatus.load_mdd_status()
            self.start(10, 30)

    def tick(self):
        req = get_mdd_status()
        if req == None:
            return
        else:
            currentStatus = req
        record_mdd_status(currentStatus, datetime.now())
        if currentStatus != self.prevStatus:
            self.prevStatus = currentStatus
            MonitorMddStatus.dump_mdd_status(currentStatus)
            groupTasks = []
            if currentStatus:
                for group in get_plugin_enabled_groups('mddmonitor'):
                    send(group, '📣交大闵行麦当劳 已▶️开放营业')
                    # groupTasks.append(aioSend(group, '📣交大闵行麦当劳 已▶️开放营业'))

            else:
                for group in get_plugin_enabled_groups('mddmonitor'):
                    send(group, '📣交大闵行麦当劳 已⏸️暂停营业')
                    # groupTasks.append(aioSend(group, '📣交大闵行麦当劳 已⏸️暂停营业'))
            return
            asyncio.run(asyncio.wait(groupTasks))
            time.sleep(1)
            subscribeUsers = list(SubscribeMdd.get_mdd_subscribers())
            subscribeUsersGroupped = [
                subscribeUsers[i: i + 5] for i in range(0, len(subscribeUsers), 5)
            ]
            for group in subscribeUsersGroupped:
                if currentStatus:
                    privateTasks = [aio_send(qq, '📣交大闵行麦当劳 已▶️开放营业', 'private') for qq in group]
                else:
                    privateTasks = [aio_send(qq, '📣交大闵行麦当劳 已⏸️暂停营业', 'private') for qq in group]
                asyncio.run(asyncio.wait(privateTasks))
                time.sleep(1)

    def judge_trigger(self, msg: str, data: Any) -> bool:
        return False

    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        return "OK"

    def get_plugin_info(self) -> dict:
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


def get_mdd_status() -> Union[None, bool]:
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
