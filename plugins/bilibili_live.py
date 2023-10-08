from utils.basic_configs import ROOT_PATH
from utils.response_image import *
from utils.sql_utils import new_sql_session
from utils.basic_event import send, warning
from typing import Union, Tuple, Any, List, Optional
from utils.standard_plugin import StandardPlugin, CronStandardPlugin
from utils.config_api import get_plugin_enabled_groups
from threading import Timer, Semaphore
from utils.bilibili_api_fixed import LiveRoomFixed
from bilibili_api.exceptions import LiveException, ApiException, ResponseCodeException
from datetime import datetime
import os.path, random


def create_bilibili_live_sql():
    mydb, mycursor = new_sql_session(autocommit=True)
    mycursor.execute("""create table if not exists `biliLiveStatus`(
        `liveId` bigint unsigned not null,
        `liveStatus` bool not null,
        `beginTime` timestamp default null,
        primary key (`liveId`)
    )""")


class GetBilibiliLive(StandardPlugin):
    def __init__(self, liveId: int, description: str, triggerPatter: str) -> None:
        self.liveId = liveId
        self.liveDescription = description
        self.triggerPattern = triggerPatter
        self.liveRoom = LiveRoomFixed(self.liveId)

    def judge_trigger(self, msg: str, data: Any) -> bool:
        return msg == self.triggerPattern

    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type'] == 'group' else data['user_id']
        try:
            roomInfo = self.liveRoom.get_room_info()['room_info']
        except LiveException as e:
            warning("bilibili api exception: {}".format(e))
            return
        except ApiException as e:
            warning('bilibili api exception: {}'.format(e))
            return
        except BaseException as e:
            warning('base exception in GetBilibiliLive: {}'.format(e))
            return
        if roomInfo['live_status'] == 1:
            savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'biliLive-%s-%d.png' % (self.liveDescription, target))
            gen_live_pic(roomInfo, '%s直播间状态' % self.liveDescription, savePath)
            send(target, f'[CQ:image,file=files:///{savePath}]', data['message_type'])
        else:
            send(target, '当前时段未开播哦', data['message_type'])
        return "OK"

    def get_plugin_info(self) -> dict:
        return {
            'name': 'GetBilibiliLive',
            'description': '%sB站直播间状态' % self.liveDescription,
            'commandDescription': self.triggerPattern,
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.3',
            'author': 'Unicorn',
        }


class BilibiliLiveMonitor(StandardPlugin, CronStandardPlugin):
    initGuard = Semaphore()

    def __init__(self, liveId: int, description: str, targetGroup: str) -> None:
        """监测B站直播间状态
        @liveId: 直播间编号
        @description: 直播间简易描述
        @targetGroup: 开播信息向哪个插件组广播
        """
        self.liveId = liveId
        self.description = description
        self.targetGroup = targetGroup
        self.liveRoom = LiveRoomFixed(self.liveId)
        self.prevStatus = False  # false: 未开播, true: 开播
        if self.initGuard.acquire(blocking=False):
            create_bilibili_live_sql()
        prevStatus = self.load_live_status()
        self.prevStatus = prevStatus if prevStatus != None else False
        self.start(5, 21 + random.randint(0, 19))

    def dump_live_status(self, status: bool):
        mydb, mycursor = new_sql_session(autocommit=True)
        mycursor.execute("""replace into `biliLiveStatus`
        (`liveId`, `liveStatus`) values (%s, %s)
        """, (self.liveId, status))

    def load_live_status(self, ) -> Optional[bool]:
        mydb, mycursor = new_sql_session(autocommit=True)
        mycursor.execute("""select `liveStatus` from `biliLiveStatus`
        where `liveId` = %s""", (self.liveId,))
        result = list(mycursor)
        if len(result) == 0:
            return None
        return result[0][0]

    def tick(self):
        try:
            roomInfo = self.liveRoom.get_room_info()['room_info']
        except ResponseCodeException as e:
            print(e)
            return
        currentStatus = roomInfo['live_status'] == 1
        if currentStatus != self.prevStatus:
            self.prevStatus = currentStatus
            self.dump_live_status(currentStatus)
            if currentStatus:
                savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'biliLive-%d.png' % self.liveId)
                gen_live_pic(roomInfo, '%s直播间状态' % self.description, savePath, useCover=True)
                for group in get_plugin_enabled_groups(self.targetGroup):
                    send(group,
                         '检测到%s开播，B站直播地址： https://live.bilibili.com/%d' % (self.description, self.liveId))
                    send(group, f'[CQ:image,file=files:///{savePath}]')

    def judge_trigger(self, msg: str, data: Any) -> bool:
        return False

    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        return "OK"

    def get_plugin_info(self) -> dict:
        return {
            'name': 'BilibiliLiveMonitor',
            'description': '广播%sB站开播信息' % self.description,
            'commandDescription': 'None',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.3',
            'author': 'Unicorn',
        }


def gen_live_pic(roomInfo, title, savePath, useCover=False) -> str:
    """
    @roomInfo: Dict
    @title:    card title
    @savePath: card image save path
    @useCover:
        if True: then gen card using roomInfo['cover']
        else:    then gen card using roomInfo['keyframe']
    """
    img = ResponseImage(
        theme='unicorn',
        title=title,
        titleColor=PALETTE_SJTU_GREEN,
        primaryColor=PALETTE_SJTU_RED,
        footer=datetime.now().strftime('当前时间 %Y-%m-%d %H:%M:%S'),
        layout='normal'
    )
    img.add_card(
        ResponseImage.NoticeCard(
            title=roomInfo['title'],
            subtitle=datetime.fromtimestamp(roomInfo['live_start_time']).strftime(
                "开播时间  %Y-%m-%d %H:%M:%S"),
            keyword='直播分区： ' + roomInfo['area_name'],
            body=roomInfo['description'],
            illustration=roomInfo['cover'] if useCover else roomInfo['keyframe'],
        )
    )
    img.generate_image(savePath)
    return savePath
