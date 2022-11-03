from utils.basicConfigs import ROOT_PATH
from utils.responseImage import *
from utils.basicEvent import send, warning
from typing import Union, Tuple, Any, List
from utils.standardPlugin import StandardPlugin, PluginGroupManager
from utils.basicEvent import getPluginEnabledGroups
from threading import Timer
from bilibili_api.live import LiveRoom
from bilibili_api.exceptions.LiveException import LiveException
from bilibili_api.exceptions.ApiException import ApiException
from datetime import datetime
import os.path
import asyncio
class FduMcLiveStatus(StandardPlugin):
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
        self.liveRoom = LiveRoom(self.liveId)
        self.timer = Timer(5, self.sjmcMonitor)
        self.timer.start()
        self.exactPath = 'data/fdmcLive.json'
        self.prevStatus = False # false: 未开播, true: 开播
        self.sjmcQqGroup = 712514518
        if not os.path.isfile(self.exactPath):
            FduMcLiveStatus.dumpSjmcStatus(False)
        else:
            self.prevStatus = FduMcLiveStatus.loadSjmcStatus()
    def sjmcMonitor(self):
        # print('mctick')
        self.timer.cancel()
        self.timer = Timer(60,self.sjmcMonitor)
        self.timer.start()
        prevStatus = FduMcLiveStatus.loadSjmcStatus()
        roomInfo = asyncio.run(self.liveRoom.get_room_info())['room_info']
        currentStatus = roomInfo['live_status'] == 1
        if currentStatus != prevStatus:
            FduMcLiveStatus.dumpSjmcStatus(currentStatus)
            if currentStatus and self.sjmcQqGroup in getPluginEnabledGroups('sjmc'):
                savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'fdmcLive.png')
                send(self.sjmcQqGroup, '检测到基岩社B站开播，基岩社直播地址： https://live.bilibili.com/%d'%self.liveId)
                genLivePic(roomInfo, '基岩社直播间状态', savePath)
                send(self.sjmcQqGroup, f'[CQ:image,file=files://{savePath},id=40000]')
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg == '-fdmclive'
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        try:
            roomInfo = asyncio.run(self.liveRoom.get_room_info())['room_info']
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
            send(target, f'[CQ:image,file=files://{savePath},id=40000]', data['message_type'])
        else:
            send(target, '当前时段未开播哦', data['message_type'])
        return "OK"
    def getPluginInfo(self) -> dict:
        return {
            'name': 'sjmclive',
            'description': '基岩社B站直播间状态',
            'commandDescription': '-fdmclive',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.3',
            'author': 'Unicorn',
        }
class SjmcLiveStatus(StandardPlugin):
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
        self.liveRoom = LiveRoom(self.liveId)
        self.timer = Timer(5, self.sjmcMonitor)
        self.timer.start()
        self.exactPath = 'data/sjmcLive.json'
        self.prevStatus = False # false: 未开播, true: 开播
        self.sjmcQqGroup = 712514518
        if not os.path.isfile(self.exactPath):
            SjmcLiveStatus.dumpSjmcStatus(False)
        else:
            self.prevStatus = SjmcLiveStatus.loadSjmcStatus()
    def sjmcMonitor(self):
        # print('mctick')
        self.timer.cancel()
        self.timer = Timer(60,self.sjmcMonitor)
        self.timer.start()
        prevStatus = SjmcLiveStatus.loadSjmcStatus()
        roomInfo = asyncio.run(self.liveRoom.get_room_info())['room_info']
        currentStatus = roomInfo['live_status'] == 1
        if currentStatus != prevStatus:
            SjmcLiveStatus.dumpSjmcStatus(currentStatus)
            if currentStatus and self.sjmcQqGroup in getPluginEnabledGroups('sjmc'):
                send(self.sjmcQqGroup, '检测到MC社B站开播，SJMC社直播地址： https://live.bilibili.com/%d'%self.liveId)
                savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'sjmcLive.png')
                genLivePic(roomInfo, 'sjmc直播间状态', savePath)
                send(self.sjmcQqGroup, f'[CQ:image,file=files://{savePath},id=40000]')

    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg in ['-mclive', '-sjmclive']
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        try:
            roomInfo = asyncio.run(self.liveRoom.get_room_info())['room_info']
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
            send(target, f'[CQ:image,file=files://{savePath},id=40000]', data['message_type'])
        else:
            send(target, '当前时段未开播哦', data['message_type'])
        return "OK"
    def getPluginInfo(self) -> dict:
        return {
            'name': 'sjmclive',
            'description': '交大MC社B站直播间状态',
            'commandDescription': '-mclive/-sjmclive',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.3',
            'author': 'Unicorn',
        }
def genLivePic(roomInfo, title, savePath)->str:
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
            illustration = roomInfo['keyframe'],
        )
    )
    img.generateImage(savePath)
    return savePath