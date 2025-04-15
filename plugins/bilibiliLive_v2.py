import copy
import os.path
import random
import time
from datetime import datetime
from threading import Semaphore, Timer
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from bilibili_api.exceptions import (ApiException, LiveException,
                                     ResponseCodeException)

from utils.basicConfigs import APPLY_GROUP_ID, ROOT_PATH
from utils.basicEvent import gocqQuote, send, warning
from utils.bilibili_api_fixed import LiveRoomFixed
from utils.configAPI import getPluginEnabledGroups
from utils.responseImage import *
from utils.sqlUtils import newSqlSession
from utils.standardPlugin import CronStandardPlugin, Job, StandardPlugin


def createBilibiliLiveSql():
    mydb, mycursor = newSqlSession(autocommit=True)
    mycursor.execute("""create table if not exists `biliLiveStatus`(
        `liveId` bigint unsigned not null,
        `liveStatus` bool not null,
        `beginTime` timestamp default null,
        primary key (`liveId`)
    )""")
    mycursor.execute("""
    create table if not exists `bilibiliLiveSubscribe` (
        `group_id` bigint unsigned not null,
        `live_id` bigint unsigned not null,
        primary key(`group_id`, `live_id`)
    )""")

# API from https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/live/info.md#%E6%89%B9%E9%87%8F%E6%9F%A5%E8%AF%A2%E7%9B%B4%E6%92%AD%E9%97%B4%E7%8A%B6%E6%80%81
class BilibiliLiveHelper(StandardPlugin):
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg in ['直播间帮助']
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        group_id = data['group_id']
        send(group_id,'直播间帮助: 直播间帮助\n' 
                    '订阅直播间:   直播间 <liveid>\n'
                    '取消订阅直播间: 取消直播间 <liveid>\n'
                    '获取直播间列表: 直播间\n'
                    '注意:  关闭本插件会自动取消所有已订阅的直播间')
        return "OK"
    def getPluginInfo(self) -> dict:
        return {
            'name': 'BilibiliLiveHelper',
            'description': 'B站直播间订阅帮助',
            'commandDescription': '直播间帮助',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }

class BilibiliLiveSubscribe(StandardPlugin, CronStandardPlugin):
    initGuard = Semaphore()
    def __init__(self) -> None:
        """
        self.bUps: liveid -> UserFixed
        self.groupUps: group_id -> Set[liveid: int]
        """
        if self.initGuard.acquire(blocking=False):
            createBilibiliLiveSql()
        self.pattern1 = re.compile(r'^直播间\s*(\d+)$')
        self.pattern2 = re.compile(r'^取消直播间\s*(\d+)$')
        self.pattern3 = re.compile(r'^直播间$')
        self.bUps:Dict[int, BilibiliLiveMonitor] = {}
        self.groupUps:Dict[int, Set[int]] = {}
        self._loadFromSql()
    def _loadFromSql(self)->None:
        mydb, mycursor = newSqlSession()
        mycursor.execute("""
        select group_id, live_id from `bilibiliLiveSubscribe`
        """)
        for group_id, live_id in list(mycursor):
            if group_id not in self.groupUps.keys():
                self.groupUps[group_id] = set()
            if live_id not in self.bUps.keys():
                self.bUps[live_id] = BilibiliLiveMonitor(live_id)
            self.groupUps[group_id].add(live_id)
            if group_id in APPLY_GROUP_ID:
                self.bUps[live_id].addGroup(group_id)
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return self.pattern1.match(msg) != None or\
               self.pattern2.match(msg) != None or\
               self.pattern3.match(msg) != None

    def subscribeBilibiliLive(self, group_id:int, bilibili_liveid:int)->None:
        if group_id not in self.groupUps.keys():
            self.groupUps[group_id] = set()
        if bilibili_liveid not in self.groupUps[group_id]:
            self.groupUps[group_id].add(bilibili_liveid)
            mydb, mycursor = newSqlSession()
            mycursor.execute("""
            insert ignore into `bilibiliLiveSubscribe` set
            group_id = %d,
            live_id = %d
            """%(group_id, bilibili_liveid))
        if bilibili_liveid not in self.bUps.keys():
            self.bUps[bilibili_liveid] = BilibiliLiveMonitor(bilibili_liveid)
        self.bUps[bilibili_liveid].addGroup(group_id)
    def unsubscribeBilibiliLive(self, group_id:int, bilibili_liveid:int)->None:
        if group_id in self.groupUps.keys() and bilibili_liveid in self.groupUps[group_id]:
            self.groupUps[group_id].discard(bilibili_liveid)
            mydb, mycursor = newSqlSession()
            mycursor.execute("""
            delete from `bilibiliLiveSubscribe` where
            group_id = %d and
            live_id = %d
            """%(group_id, bilibili_liveid))
        if bilibili_liveid in self.bUps.keys():
            self.bUps[bilibili_liveid].delGroup(group_id)

    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        group_id = data['group_id']
        if self.pattern1.match(msg) != None:
            liveid = self.pattern1.findall(msg)[0]
            liveid = int(liveid)
            try:
                room = LiveRoomFixed(liveid)
                roomInfo = room.get_room_info()
                self.subscribeBilibiliLive(group_id, liveid)
                name = gocqQuote(room['name'])
                send(group_id, f'订阅成功！\nname: {name}\nliveid: {liveid}')
            except ResponseCodeException as e:
                send(group_id, f'好像没找到这个直播间:\n{e}')
            except KeyError as e:
                warning('bilibili api get_user_info error: {}'.format(e))
        elif self.pattern2.match(msg) != None:
            liveid = self.pattern2.findall(msg)[0]
            liveid = int(liveid)
            self.unsubscribeBilibiliLive(group_id, liveid)
            send(group_id, '[CQ:reply,id=%d]OK'%data['message_id'])
        elif self.pattern3.match(msg) != None:
            ups = self.subscribeList(group_id)
            if len(ups) == 0:
                send(group_id, '[CQ:reply,id=%d]本群还没有订阅直播间哦~'%data['message_id'])
            else:
                try:
                    metas = [up.get_room_info() for up in ups]
                    metas = [f"name: {m['name']}\nliveid: {m['mid']}" for m in metas]
                    send(group_id,f'本群订阅的直播间有：\n\n'+'\n----------\n'.join(metas))
                except BaseException as e:
                    send(group_id, 'bilibili api error')
                    warning('bilibili get_user_info error: {}'.format(e))
        return "OK"
    def onStateChange(self, nextState: bool, data: Any) -> None:
        group_id = data['group_id']
        if nextState or group_id not in self.groupUps.keys(): return
        for liveid in copy.deepcopy(self.groupUps[group_id]):
            self.unsubscribeBilibili(group_id, liveid)
    
    def subscribeList(self, group_id:int)->List[LiveRoomFixed]:
        liveids = self.groupUps.get(group_id, set())
        return [self.bUps[liveid].bUser for liveid in liveids]

    def getPluginInfo(self) -> dict:
        return {
            'name': 'BilibiliLiveSubscribe',
            'description': '订阅B站直播间',
            'commandDescription': '直播间/直播间 <liveid>/取消直播间 <liveid>',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
    def __init__(self, liveid:int) -> None:
        self.bidToGroup:Dict[int,List[int]] = liveid
        self.job: Optional[Job] = None

        self.cumulativeNetworkErrCount = 0
        # _prevMeta: [prevUploadTime, prevDynamicId]
        self._prevMeta:Optional[Tuple[int, int]] = None
        self.baseInterval = 25 + random.randint(0, 10)
    def getLiveInfo(self)->Optional[Dict[str, Any]]:
        if len(self.bidToGroup) == 0:
            return []
        result = requests.post('https://api.live.bilibili.com/room/v1/Room/get_status_info_by_uids', json={
            'uids': list(self.bidToGroup.keys())
        }).json()
        if result['code'] != 0:
            return None
        return result['data']
    def addMonitoringTarget(self, group_id:int, live_id:int)->bool:
        if live_id in self.bidToGroup.keys():
            if group_id in self.bidToGroup[live_id]:
                return False
            self.bidToGroup[live_id].append(group_id)
        else:
            self.bidToGroup[live_id] = [group_id]
        mydb, mycursor = newSqlSession()
        mycursor.execute("""insert ignore into `bilibiliLiveSubscribe`
        (`group_id`, `live_id`) values (%d, %d)
        """%(group_id, live_id))
        return True
    def delMonitoringTarget(self, group_id:int, live_id:int)->bool:
        if live_id not in self.bidToGroup.keys():
            return False
        if group_id not in self.bidToGroup[live_id]:
            return False
        self.bidToGroup[live_id].remove(group_id)
        if len(self.bidToGroup[live_id]) == 0:
            del self.bidToGroup[live_id]
        mydb, mycursor = newSqlSession()
        mycursor.execute("""delete from `bilibiliLiveSubscribe` where
        `group_id` = %d and `live_id` = %d
        """%(group_id, live_id))
        return True

    def tick(self) -> None:
        if len(self.bidToGroup) == 0:
            return
        liveData = self.getLiveInfo()
        
        
    def writeMeta(self, uploadTime:int, dynamicId:int)->None:
        """写入up主本次上传数据"""
        meta = (uploadTime, dynamicId)
        self._prevMeta = meta
        mydb, mycursor = newSqlSession()
        print(uploadTime, dynamicId, self.uid)
        mycursor.execute("""
        replace into `bilibiliDynamic` set
        uploadTime = from_unixtime(%s),
        dynamicId = %s,
        uid = %s
        """, (uploadTime, dynamicId, self.uid))

    def cancel(self,) -> None:
        if self.job != None: 
            self.job.remove()
    def pause(self) -> None:
        if self.job != None:
            self.job.pause()
    def resume(self) -> None:
        if self.job != None:
            self.job.resume()
    def __del__(self,):
        self.cancel()
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