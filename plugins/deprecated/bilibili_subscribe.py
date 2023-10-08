from utils.standard_plugin import StandardPlugin, CronStandardPlugin, Job
from utils.sql_utils import new_sql_session
from utils.basic_event import send, warning, gocq_quote
import re
from typing import List, Tuple, Optional, Union, Dict, Any, Set
from utils.bilibili_api_fixed import UserFixed
from bilibili_api.exceptions.ResponseCodeException import ResponseCodeException
import random
from threading import Semaphore
import copy
import time


def bv_to_url(bvid: str):
    return 'https://www.bilibili.com/video/' + bvid


def create_bilibili_table() -> None:
    mydb, mycursor = new_sql_session()
    mycursor.execute("""
    create table if not exists `bilibiliUp` (
       `uid` bigint unsigned not null,
       `uploadTime` timestamp not null,
       `bvid` char(20) not null,
       primary key (`uid`)
    )""")
    mycursor.execute("""
    create table if not exists `bilibiliSubscribe` (
        `group_id` bigint unsigned not null,
        `uid` bigint unsigned not null,
        primary key(`group_id`, `uid`)
    )""")


class BilibiliSubscribeHelper(StandardPlugin):
    def judge_trigger(self, msg: str, data: Any) -> bool:
        return msg in ["B站订阅帮助", "b站订阅帮助"] and data['message_type'] == 'group'

    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        group_id = data['group_id']
        send(group_id, '订阅帮助: B站订阅帮助\n'
                       '订阅up:    订阅 <uid>\n'
                       '取消订阅: 取消订阅 <uid>\n'
                       '获取订阅列表: 订阅\n'
                       '注意:  关闭本插件会自动取消所有已订阅的up')
        return "OK"

    def get_plugin_info(self) -> dict:
        return {
            'name': 'BilibiliSubscribeHelper',
            'description': 'B站订阅帮助',
            'commandDescription': 'B站订阅帮助',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }


class BilibiliUpSearcher(StandardPlugin):
    def __init__(self) -> None:
        self.pattern = re.compile(r'^搜索up\s*(\S+)$')

    def judge_trigger(self, msg: str, data: Any) -> bool:
        return self.pattern.match(msg) != None

    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        return "OK"

    def get_plugin_info(self) -> dict:
        return {
            'name': 'BilibiliUpSearcher',
            'description': '搜索B站用户uid',
            'commandDescription': '搜索up <name>',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }


class BilibiliSubscribe(StandardPlugin):
    initGuard = Semaphore()

    def __init__(self) -> None:
        """
        self.bUps: uid -> UserFixed
        self.groupUps: group_id -> Set[uid: int]
        """
        if self.initGuard.acquire(blocking=False):
            create_bilibili_table()
        self.pattern1 = re.compile(r'^订阅\s*(\d+)$')
        self.pattern2 = re.compile(r'^取消订阅\s*(\d+)$')
        self.pattern3 = re.compile(r'^订阅$')
        self.bUps: Dict[int, BilibiliMonitor] = {}
        self.groupUps: Dict[int, Set[int]] = {}
        self._load_from_sql()

    def _load_from_sql(self) -> None:
        mydb, mycursor = new_sql_session()
        mycursor.execute("""
        select group_id, uid from `bilibiliSubscribe`
        """)
        for group_id, uid in list(mycursor):
            if group_id not in self.groupUps.keys():
                self.groupUps[group_id] = set()
            if uid not in self.bUps.keys():
                self.bUps[uid] = BilibiliMonitor(uid)
            self.groupUps[group_id].add(uid)
            self.bUps[uid].add_group(group_id)

    def judge_trigger(self, msg: str, data: Any) -> bool:
        return self.pattern1.match(msg) != None or \
            self.pattern2.match(msg) != None or \
            self.pattern3.match(msg) != None

    def subscribeBilibili(self, group_id: int, bilibili_uid: int) -> None:
        if group_id not in self.groupUps.keys():
            self.groupUps[group_id] = set()
        if bilibili_uid not in self.groupUps[group_id]:
            self.groupUps[group_id].add(bilibili_uid)
            mydb, mycursor = new_sql_session()
            mycursor.execute("""
            insert ignore into `bilibiliSubscribe` set
            group_id = %d,
            uid = %d
            """ % (group_id, bilibili_uid))
        if bilibili_uid not in self.bUps.keys():
            self.bUps[bilibili_uid] = BilibiliMonitor(bilibili_uid)
        self.bUps[bilibili_uid].add_group(group_id)

    def unsubscribeBilibili(self, group_id: int, bilibili_uid: int) -> None:
        if group_id in self.groupUps.keys() and bilibili_uid in self.groupUps[group_id]:
            self.groupUps[group_id].discard(bilibili_uid)
            mydb, mycursor = new_sql_session()
            mycursor.execute("""
            delete from `bilibiliSubscribe` where
            group_id = %d and
            uid = %d
            """ % (group_id, bilibili_uid))
        if bilibili_uid in self.bUps.keys():
            self.bUps[bilibili_uid].del_group(group_id)

    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        group_id = data['group_id']
        if self.pattern1.match(msg) != None:
            uid = self.pattern1.findall(msg)[0]
            uid = int(uid)
            try:
                u = UserFixed(uid)
                userInfo = u.get_user_info()
                self.subscribeBilibili(group_id, uid)
                name = gocq_quote(userInfo['name'])
                send(group_id, f'订阅成功！\nname: {name}\nuid: {uid}')
            except ResponseCodeException as e:
                send(group_id, f'好像没找到这个UP:\n{e}')
            except KeyError as e:
                warning('bilibili api get_user_info error: {}'.format(e))
        elif self.pattern2.match(msg) != None:
            uid = self.pattern2.findall(msg)[0]
            uid = int(uid)
            self.unsubscribeBilibili(group_id, uid)
            send(group_id, '[CQ:reply,id=%d]OK' % data['message_id'])
        elif self.pattern3.match(msg) != None:
            ups = self.subscribeList(group_id)
            if len(ups) == 0:
                send(group_id, '[CQ:reply,id=%d]本群还没有订阅up哦~' % data['message_id'])
            else:
                try:
                    metas = [up.get_user_info() for up in ups]
                    metas = [f"name: {m['name']}\nuid: {m['mid']}" for m in metas]
                    send(group_id, f'本群订阅的up有：\n\n' + '\n----------\n'.join(metas))
                except BaseException as e:
                    send(group_id, 'bilibili api error')
                    warning('bilibili get_user_info error: {}'.format(e))
        return "OK"

    def on_state_change(self, nextState: bool, data: Any) -> None:
        group_id = data['group_id']
        if nextState or group_id not in self.groupUps.keys(): return
        for uid in copy.deepcopy(self.groupUps[group_id]):
            self.unsubscribeBilibili(group_id, uid)

    def subscribeList(self, group_id: int) -> List[UserFixed]:
        uids = self.groupUps.get(group_id, set())
        return [self.bUps[uid].bUser for uid in uids]

    def get_plugin_info(self) -> dict:
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


class BilibiliMonitor(CronStandardPlugin):
    """bilibili up主监控类
    self.uid: 被监控的up主uid
    self.groupList
    """

    def __init__(self, uid: int) -> None:
        self.uid: int = uid
        self.bUser = UserFixed(uid=uid)
        self.groupList = set()
        self.job: Optional[Job] = None

        self.cumulativeNetworkErrCount = 0
        self._prevMeta: Optional[Tuple[int, str]] = None
        self.baseInterval = 3 * 60 + random.randint(0, 100)

    def add_group(self, group_id: int):
        self.groupList.add(group_id)
        if self.job == None:
            self.job = self.start(0, self.baseInterval)
        else:
            self.resume()

    def del_group(self, group_id: int):
        self.groupList.discard(group_id)
        if len(self.groupList) == 0:
            self.pause()

    def tick(self) -> None:
        videos = None
        try:
            videos = self.bUser.get_videos()
        except BaseException as e:
            videos = None
            time.sleep(3)
        if videos == None:
            self.cumulativeNetworkErrCount += 1
            if self.cumulativeNetworkErrCount >= 3:
                # warning('bilibili subscribe api failed!')
                self.cumulativeNetworkErrCount = 0
                self.cancel()
                self.baseInterval += random.randint(0, 100)
                self.job = self.start(0, self.baseInterval)
            return
        else:
            self.cumulativeNetworkErrCount = 0

        try:
            videos = videos['list']['vlist']
            if len(videos) == 0: return
            latestVideo = max(videos, key=lambda x: x['created'])
            uploadTime = latestVideo['created']
            bvid = latestVideo['bvid']
            prevMeta = self.get_prev_meta()
            if prevMeta == None or prevMeta != (uploadTime, bvid):
                self.write_meta(uploadTime, bvid)
                title = gocq_quote(latestVideo['title'])
                author = gocq_quote(latestVideo['author'])
                for group in self.groupList:
                    send(group, f'本群订阅UP主 【{author}】 更新视频啦！\n视频标题： {title}\n链接：{bv_to_url(bvid)}')
        except KeyError as e:
            warning('bilibili api has changed!')
            self.cancel()
            return
        except BaseException as e:
            warning('base excption in BilibiliMonitor: {}'.format(e))
            self.cancel()

    def get_prev_meta(self) -> Optional[Tuple[int, str]]:
        """获取该up主记录在册的前一次上传数据
        @return: Optional[(
            [0]: int: uploadTime unix时间戳
            [1]: str: bvid
        )]
        """
        if self._prevMeta == None:
            mydb, mycursor = new_sql_session()
            mycursor.execute("""
            select unix_timestamp(uploadTime), bvid from `bilibiliUp` where
            uid = %d
            """ % self.uid)
            meta = list(mycursor)
            if len(meta) != 0:
                self._prevMeta = meta[0]
        return self._prevMeta

    def write_meta(self, uploadTime: int, bvid: str) -> None:
        """写入up主本次上传数据"""
        meta = (uploadTime, bvid)
        if self._prevMeta == meta: return

        self._prevMeta = meta
        mydb, mycursor = new_sql_session()
        mycursor.execute("""
        insert into `bilibiliUp` set
        uploadTime = from_unixtime(%s),
        bvid = %s,
        uid = %s
        on duplicate key update
        uploadTime = from_unixtime(%s),
        bvid = %s
        """, (uploadTime, bvid, self.uid, uploadTime, bvid))

    def cancel(self, ) -> None:
        if self.job != None:
            self.job.remove()

    def pause(self) -> None:
        if self.job != None:
            self.job.pause()

    def resume(self) -> None:
        if self.job != None:
            self.job.resume()

    def __del__(self, ):
        self.cancel()
