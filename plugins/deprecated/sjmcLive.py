import os.path
from datetime import datetime
from threading import Semaphore, Timer
from typing import Any, List, Tuple, Union

from bilibili_api.exceptions.ApiException import ApiException
from bilibili_api.exceptions.LiveException import LiveException

from utils.basicConfigs import ROOT_PATH
from utils.basicEvent import send, warning
from utils.bilibili_api_fixed import LiveRoomFixed
from utils.configAPI import getPluginEnabledGroups
from utils.responseImage import *
from utils.standardPlugin import CronStandardPlugin, StandardPlugin


class GetFduMcLive(StandardPlugin):
    def __init__(self) -> None:
        self.liveId = 24716629
        self.liveRoom = LiveRoomFixed(self.liveId)
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg == '-fdmclive'
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        try:
            roomInfo = self.liveRoom.get_room_info()['room_info']
        except LiveException as e:
            warning("sjmc bilibili api exception: {}".format(e))
            return
        except ApiException as e:
            warning('bilibili api exception: {}'.format(e))
            return 
        except BaseException as e:
            warning('base exception in sjmclive: {}'.format(e))
            return
        if roomInfo['live_status'] == 1:
            savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'fdmcLive-%d.png'%target)
            genLivePic(roomInfo, '基岩社直播间状态', savePath)
            send(target, f'[CQ:image,file=file:///{savePath}]', data['message_type'])
        else:
            send(target, '当前时段未开播哦', data['message_type'])
        return "OK"
    def getPluginInfo(self) -> dict:
        return {
            'name': 'GetFduMcLive',
            'description': '基岩社B站直播间状态',
            'commandDescription': '-fdmclive',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.3',
            'author': 'Unicorn',
        }
class FduMcLiveMonitor(StandardPlugin, CronStandardPlugin):
    monitorSemaphore = Semaphore()
    @staticmethod
    def dumpSjmcStatus(status: bool):
        exactPath = 'data/fdmcLive.json'
        with open(exactPath, 'w') as f:
            f.write('1' if status else '0')
    @staticmethod
    def loadSjmcStatus()->bool:
        exactPath = 'data/fdmcLive.json'
        with open(exactPath, 'r') as f:
            return f.read().startswith('1')
    def __init__(self) -> None:
        self.liveId = 24716629
        self.liveRoom = LiveRoomFixed(self.liveId)
        self.exactPath = 'data/fdmcLive.json'
        self.prevStatus = False # false: 未开播, true: 开播
        if FduMcLiveMonitor.monitorSemaphore.acquire(blocking=False):
            if not os.path.isfile(self.exactPath):
                os.makedirs('data', exist_ok=True)
                FduMcLiveMonitor.dumpSjmcStatus(self.prevStatus)
            else:
                self.prevStatus = FduMcLiveMonitor.loadSjmcStatus()
            self.start(5, 30)

    def tick(self):
        roomInfo = self.liveRoom.get_room_info()['room_info']
        currentStatus = roomInfo['live_status'] == 1
        if currentStatus != self.prevStatus:
            self.prevStatus = currentStatus
            FduMcLiveMonitor.dumpSjmcStatus(currentStatus)
            if currentStatus:
                savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'fdmcLive.png')
                genLivePic(roomInfo, '基岩社直播间状态', savePath, useCover=True)
                for group in getPluginEnabledGroups('mclive'):
                    send(group, '检测到基岩社B站开播，基岩社直播地址： https://live.bilibili.com/%d'%self.liveId)
                    send(group, f'[CQ:image,file=file:///{savePath}]')
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return False
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        return "OK"
    def getPluginInfo(self) -> dict:
        return {
            'name': 'FduMcLiveMonitor',
            'description': '广播基岩社B站直播间开播信息',
            'commandDescription': 'None',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.3',
            'author': 'Unicorn',
        }
class GetSjmcLive(StandardPlugin):
    def __init__(self) -> None:
        self.liveId = 25567444
        self.liveRoom = LiveRoomFixed(self.liveId)
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg in ['-mclive', '-sjmclive']
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        try:
            roomInfo = self.liveRoom.get_room_info()['room_info']
        except LiveException as e:
            warning("sjmc bilibili api exception: {}".format(e))
            return
        except ApiException as e:
            warning('bilibili api exception: {}'.format(e))
            return 
        except BaseException as e:
            warning('base exception in sjmclive: {}'.format(e))
            return
        if roomInfo['live_status'] == 1:
            savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'sjmcLive-%d.png'%target)
            genLivePic(roomInfo, 'sjmc直播间状态', savePath)
            send(target, f'[CQ:image,file=file:///{savePath}]', data['message_type'])
        else:
            send(target, '当前时段未开播哦', data['message_type'])
        return "OK"
    def getPluginInfo(self) -> dict:
        return {
            'name': 'GetSjmcLive',
            'description': '交大MC社B站直播间状态',
            'commandDescription': '-mclive/-sjmclive',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.3',
            'author': 'Unicorn',
        }
class SjmcLiveMonitor(StandardPlugin, CronStandardPlugin):
    monitorSemaphore = Semaphore()
    @staticmethod
    def dumpSjmcStatus(status: bool):
        exactPath = 'data/sjmcLive.json'
        with open(exactPath, 'w') as f:
            f.write('1' if status else '0')
    @staticmethod
    def loadSjmcStatus()->bool:
        exactPath = 'data/sjmcLive.json'
        with open(exactPath, 'r') as f:
            return f.read().startswith('1')
    def __init__(self) -> None:
        self.liveId = 25567444
        self.liveRoom = LiveRoomFixed(self.liveId)
        self.exactPath = 'data/sjmcLive.json'
        self.prevStatus = False # false: 未开播, true: 开播
        if SjmcLiveMonitor.monitorSemaphore.acquire(blocking=False):
            if not os.path.isfile(self.exactPath):
                os.makedirs('data', exist_ok=True)
                SjmcLiveMonitor.dumpSjmcStatus(self.prevStatus)
            else:
                self.prevStatus = SjmcLiveMonitor.loadSjmcStatus()
            self.start(5, 30)


    def tick(self):
        roomInfo = self.liveRoom.get_room_info()['room_info']
        currentStatus = roomInfo['live_status'] == 1
        if currentStatus != self.prevStatus:
            self.prevStatus = currentStatus
            SjmcLiveMonitor.dumpSjmcStatus(currentStatus)
            if currentStatus:
                savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'sjmcLive.png')
                genLivePic(roomInfo, 'sjmc直播间状态', savePath, useCover=True)
                for group in getPluginEnabledGroups('mclive'):
                    send(group, '检测到MC社B站开播，SJMC社直播地址： https://live.bilibili.com/%d'%self.liveId)
                    send(group, f'[CQ:image,file=file:///{savePath}]')
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return False
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        return "OK"
    def getPluginInfo(self) -> dict:
        return {
            'name': 'SjmcLiveMonitor',
            'description': '广播交大MC社B站直播间开播信息',
            'commandDescription': 'None',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.3',
            'author': 'Unicorn',
        }
class MuaLiveMonitor(StandardPlugin, CronStandardPlugin):
    monitorSemaphore = Semaphore()
    @staticmethod
    def dumpSjmcStatus(status: bool):
        exactPath = 'data/muaLive.json'
        with open(exactPath, 'w') as f:
            f.write('1' if status else '0')
    @staticmethod
    def loadSjmcStatus()->bool:
        exactPath = 'data/muaLive.json'
        with open(exactPath, 'r') as f:
            return f.read().startswith('1')
    def __init__(self) -> None:
        self.liveId = 30539032
        self.liveRoom = LiveRoomFixed(self.liveId)
        self.exactPath = 'data/muaLive.json'
        self.prevStatus = False # false: 未开播, true: 开播
        if self.monitorSemaphore.acquire(blocking=False):
            if not os.path.isfile(self.exactPath):
                os.makedirs('data', exist_ok=True)
                self.dumpSjmcStatus(self.prevStatus)
            else:
                self.prevStatus = self.loadSjmcStatus()
            self.start(5, 30)


    def tick(self):
        roomInfo = self.liveRoom.get_room_info()['room_info']
        currentStatus = roomInfo['live_status'] == 1
        if currentStatus != self.prevStatus:
            self.prevStatus = currentStatus
            self.dumpSjmcStatus(currentStatus)
            if currentStatus:
                savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'muaLive.png')
                genLivePic(roomInfo, 'MC高校联盟直播间状态', savePath, useCover=True)
                for group in getPluginEnabledGroups('mualive'):
                    send(group, '检测到MC高校联盟B站开播，MUA直播地址： https://live.bilibili.com/%d'%self.liveId)
                    send(group, f'[CQ:image,file=file:///{savePath}]')
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return False
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        return "OK"
    def getPluginInfo(self) -> dict:
        return {
            'name': 'MuaLiveMonitor',
            'description': '广播MUA B站直播间开播信息',
            'commandDescription': 'None',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.3',
            'author': 'Unicorn',
        }
class GetMuaLive(StandardPlugin):
    def __init__(self) -> None:
        self.liveId = 30539032
        self.liveRoom = LiveRoomFixed(self.liveId)
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg in ['-mualive', ]
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        try:
            roomInfo = self.liveRoom.get_room_info()['room_info']
        except LiveException as e:
            warning("mua bilibili api exception: {}".format(e))
            return
        except ApiException as e:
            warning('bilibili api exception: {}'.format(e))
            return 
        except BaseException as e:
            warning('base exception in mualive: {}'.format(e))
            return
        if roomInfo['live_status'] == 1:
            savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'muaLive-%d.png'%target)
            genLivePic(roomInfo, 'mua直播间状态', savePath)
            send(target, f'[CQ:image,file=file:///{savePath}]', data['message_type'])
        else:
            send(target, '当前时段未开播哦', data['message_type'])
        return "OK"
    def getPluginInfo(self) -> dict:
        return {
            'name': 'GetMuaLive',
            'description': 'MUA B站直播间状态',
            'commandDescription': '-mualive',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.3',
            'author': 'Unicorn',
        }
def genLivePic(roomInfo, title, savePath, useCover=False)->str:
    """
    @roomInfo: Dict
    @title:    card title
    @savePath: card image save path
    @useCover:
        if True: then gen card using roomInfo['cover']
        else:    then gen card using roomInfo['keyframe']
    """
    img = ResponseImage(
        theme = 'unicorn',
        title = title, 
        titleColor = PALETTE_SJTU_GREEN, 
        primaryColor = PALETTE_SJTU_RED, 
        footer = datetime.now().strftime('当前时间 %Y-%m-%d %H:%M:%S'),
        layout = 'normal'
    )
    img.addCard(
        ResponseImage.NoticeCard(
            title = roomInfo['title'],
            subtitle = datetime.fromtimestamp(roomInfo['live_start_time']).strftime(
                                                "开播时间  %Y-%m-%d %H:%M:%S"),
            keyword = '直播分区： '+roomInfo['area_name'],
            body = roomInfo['description'],
            illustration = roomInfo['cover'] if useCover else roomInfo['keyframe'],
        )
    )
    img.generateImage(savePath)
    return savePath