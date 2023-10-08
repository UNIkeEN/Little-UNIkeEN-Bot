from utils.basic_event import send, warning, get_group_msg_history
from utils.standard_plugin import StandardPlugin, CronStandardPlugin
from typing import Optional, List, Dict, Any, Union, Tuple
from utils.config_api import get_plugin_enabled_groups
from utils.basic_configs import IMAGES_PATH, ROOT_PATH
from utils.sql_utils import new_sql_session
from pymysql.converters import escape_string
from threading import Semaphore
import time
import os


def create_advertisement_sql():
    mydb, mycursor = new_sql_session()
    mycursor.execute("""
    create table if not exists `advertisementContext`(
        `group_id` bigint unsigned not null,
        `unique_key` char(64) not null,
        `last_message_seq` bigint,
        `last_time` timestamp,
        primary key(`group_id`, `unique_key`)
    )charset=utf8mb4, collate=utf8mb4_unicode_ci;""")


def get_latest_seq_and_time(group_id: int) -> Optional[Tuple[int, int]]:
    currentTime = int(time.time())
    msgs = get_group_msg_history(group_id)
    if len(msgs) > 0:
        latestMsg = max(msgs, key=lambda x: x['message_seq'])
        return latestMsg['message_seq'], max(latestMsg['time'], currentTime)
    else:
        mydb, mycursor = new_sql_session()
        mycursor.execute("""
        select `message_seq`, unix_timestamp(`time`) from `messageRecord`
        where group_id = %d order by `message_seq` desc limit 1;
        """ % (group_id,))
        result = list(mycursor)
        if len(result) == 0:
            return None
        else:
            return result[0][0], max(result[0][1], currentTime)


class BaseAdvertisementClass(CronStandardPlugin):
    initGuard = Semaphore()

    def __init__(self, adword: str, group_id: int, uniqueKey: str, deltaTime: int, deltaMsg: int):
        """
        @group_id: 投放广告的目标群组
        @uniqueKey: 广告唯一标识（不同群可重合）
        @deltaTime: 广告最短间隔时间，单位 [second]
        @deltaMsg:  广告最短间隔消息条数，单位 [条]
        """
        if self.initGuard.acquire(blocking=False):
            create_advertisement_sql()
        assert isinstance(uniqueKey, str) and len(uniqueKey) < 64
        self.adword = adword
        self.group_id = group_id
        self.uniqueKey = uniqueKey
        self.deltaTime = deltaTime
        self.deltaMsg = deltaMsg
        lastMsgSeq, lastTime = self.load_context()
        self.lastMsgSeq = lastMsgSeq
        self.lastTime = lastTime

        if lastMsgSeq == None or lastTime == None:
            lastMsgSeq, lastTime = get_latest_seq_and_time(self.group_id)
            self.dump_context(lastMsgSeq, lastTime)

        self.job = self.start(0, 20)  # check every 20s

    def tick(self):
        latestSeq, latestTime = get_latest_seq_and_time(self.group_id)
        # print(f'latestSeq: {latestSeq}, lastSeq: {self.lastMsgSeq}\nlatestTime: {latestTime}, lastTime: {self.lastTime}')
        if self.judge_satisfy(latestSeq, latestTime):
            send(self.group_id, self.adword)
            self.dump_context(latestSeq, latestTime)

    def load_context(self) -> Tuple[Optional[int], Optional[int]]:
        """
        @return: Tuple[last_message_seq, last_time]
        """
        mydb, mycursor = new_sql_session()
        mycursor.execute("""
        select `last_message_seq`, unix_timestamp(`last_time`) from `advertisementContext`
        where group_id = %d and unique_key = '%s'""" % (
            self.group_id, escape_string(self.uniqueKey)
        ))
        result = list(mycursor)
        if len(result) == 0:
            return None, None
        else:
            return result[0]

    def dump_context(self, lastMsgSeq: int, lastTime: int):
        mydb, mycursor = new_sql_session()
        mycursor.execute("""replace into `advertisementContext`
        (`last_message_seq`,`last_time`,`group_id`, `unique_key`) 
        values (%d, from_unixtime(%d), %d, '%s')
        """ % (
            lastMsgSeq, lastTime,
            self.group_id, escape_string(self.uniqueKey)
        ))
        self.lastMsgSeq = lastMsgSeq
        self.lastTime = lastTime

    def judge_satisfy(self, latestSeq: int, latestTime: int):
        return (latestTime - self.lastTime >= self.deltaTime and
                latestSeq - self.lastMsgSeq >= self.deltaMsg)

    def cancel(self):
        if self.job != None:
            self.job.remove()
            self.job = None

    def is_valid(self):
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
        #     f"[CQ:image,file=files:///{os.path.join(ROOT_PATH, IMAGES_PATH, 'mc.png')}]"
        #     "进群看学长女装~"
        # )
        self.adword = (
            '问 mc'
        )
        self.uniqueKey = 'sjmcad'
        # self.deltaTime = 0 # 40 min
        # self.deltaMsg = 0  # 100 msg 
        self.deltaTime = 60 * 60  # 60 min
        self.deltaMsg = 150  # 150 msg
        for group_id in get_plugin_enabled_groups('mcad'):
            self.groups[group_id] = BaseAdvertisementClass(self.adword, group_id, self.uniqueKey, self.deltaTime,
                                                           self.deltaMsg)

    def judge_trigger(self, msg: str, data: Any) -> bool:
        return False

    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        return None

    def get_plugin_info(self) -> dict:
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

    def on_state_change(self, nextState: bool, data: Any) -> None:
        group_id = data['group_id']
        if nextState:
            self.groups[group_id] = BaseAdvertisementClass(self.adword, group_id, self.uniqueKey, self.deltaTime,
                                                           self.deltaMsg)
        else:
            if group_id in self.groups.keys():
                self.groups[group_id].cancel()
                del self.groups[group_id]
