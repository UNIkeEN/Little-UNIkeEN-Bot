from utils.standardPlugin import StandardPlugin, CronStandardPlugin, Job
from utils.sqlUtils import newSqlSession
from utils.basicEvent import send, warning, gocqQuote
from utils.responseImage_beta import *
from utils.basicConfigs import ROOT_PATH, SAVE_TMP_PATH, APPLY_GROUP_ID
import re, json
from typing import List, Tuple, Optional, Union, Dict, Any, Set
from utils.bilibili_api_fixed import UserFixed
from bilibili_api.exceptions.ResponseCodeException import ResponseCodeException
import random
from threading import Semaphore
import copy
import time, datetime
def bvToUrl(bvid:str):
    return 'https://www.bilibili.com/video/' + bvid
def dynamicIdToUrl(dynamicId:int):
    return 'https://www.bilibili.com/opus/' + str(dynamicId)
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

def durationToStr(duration:int)->str:
    if not isinstance(duration, int) or duration < 0:
        raise Exception('invalid input in durationToStr')
    hours = duration // 3600
    duration = duration % 3600
    minutes = duration // 60
    seconds = duration % 60
    if hours == 0:
        result = '%02d:%02d'%(minutes, seconds)
        return result
    else:
        result = '%d:%02d:%02d'%(hours, minutes, seconds)
        return result
def makeThumbnails(pictures:List[Dict[str, Any]]):
    """TODO: make thumbnails
    first step: aioget, if len(pic) == 1 or 2 or >= 3
    second step: 
        if height>width: resize, img = img[from:to, :, :]
        else: resize, img = img[:, from:to,:]
    third step: paste to Image
    """
def dimensionToStr(dimension:Dict[str, int])->str:
    return '%s x %s'%(dimension['width'], dimension['height'])

def drawDynamicCard(dynamicInfo:Dict[str, Any], savePath:str)->Tuple[bool, str]:
    try:
        card = ResponseImage(
            title='B站动态更新',
        )
        if isinstance(dynamicInfo['card'], str):
            try:
                dynamicInfo['card'] = json.loads(dynamicInfo['card'])
            except:
                pass
            try:
                dynamicInfo['extend_json'] = json.loads(dynamicInfo['extend_json'])
            except:
                pass
            
        pubtime = datetime.datetime.fromtimestamp(dynamicInfo['desc']['timestamp'])
        uname = dynamicInfo['desc']['user_profile']['info']['uname']
        dynamicType = dynamicInfo['desc']['type']
        if dynamicType == 8:
            # 8: 视频
            body = ''.join([
                '标题： ', dynamicInfo['card']['title'], '\n',
                '简介： ', dynamicInfo['card']['desc'], '\n',
                'IP： ', dynamicInfo['card'].get('pub_location', '未知'), '\n',
                '时长： ', durationToStr(dynamicInfo['card']['duration']), '\n',
                '链接： ', dynamicInfo['card']['short_link_v2'], '\n',
                '分辨率： ', dimensionToStr(dynamicInfo['card']['dimension'])
            ])
            coverLink = dynamicInfo['card']['pic']
            card.addCard(ResponseImage.RichContentCard([
                ('title', uname, ),
                ('subtitle', pubtime.strftime('更新于 %Y-%m-%d %H:%M:%S'),),
                ('keyword', '类型： 视频', ),
                ('separator', ),
                ('body', body, ),
                ('illustration', coverLink,),
            ]))
        elif dynamicType == 1:
            # 1: 转发动态
            body = dynamicInfo['card']['item']['content']
            card.addCard(ResponseImage.RichContentCard([
                ('title', uname, ),
                ('subtitle',pubtime.strftime('更新于 %Y-%m-%d %H:%M:%S'), ),
                ('keyword','类型： 转发动态',),
                ('separator', ),
                ('body', body, ),
            ]))
            if 'origin' in dynamicInfo['card'].keys():
                originUser = dynamicInfo['card']['origin_user']['info']['uname']
                origin = json.loads(dynamicInfo['card']['origin'])
                originPubtime = None
                if 'publish_time' in origin.keys():
                    originPubtime = datetime.datetime.fromtimestamp(origin['publish_time'])
                elif 'upload_time' in origin.keys():
                    originPubtime = datetime.datetime.fromtimestamp(origin['upload_time'])
                elif 'timestamp' in origin.keys():
                    originPubtime = datetime.datetime.fromtimestamp(origin['timestamp'])
                elif 'ctime' in origin.keys():
                    originPubtime = datetime.datetime.fromtimestamp(origin['ctime'])
                elif origin.get('item', {}).get('upload_time', None) != None:
                    originPubtime = datetime.datetime.fromtimestamp(origin['item']['upload_time'])

                originImgs = []
                for imgInfo in origin.get('pictures', []):
                    originImgs.append(('illustration', imgInfo['img_src']))
                if 'pic' in origin.keys():
                    originImgs.append(('illustration', origin['pic']))
                for imgUrl in origin.get('image_urls', []):
                    originImgs.append(('illustration', imgUrl))
                for imgInfo in origin.get('item', {}).get('pictures', []):
                    originImgs.append(('illustration', imgInfo['img_src']))
                originContents = []
                if 'title' in origin.keys():
                    originContents.append(('subtitle', origin['title']))
                if 'summary' in origin.keys():
                    originContents.append(('body', origin['summary']))
                if "description" in origin.get('item', {}).keys():
                    originContents.append(('body', origin['item']['description']))
                card.addCard(ResponseImage.RichContentCard([
                    ('title', originUser, ),
                    ('subtitle',originPubtime.strftime('更新于 %Y-%m-%d %H:%M:%S') if originPubtime != None else '未知的发布时间', ),
                    ('keyword','类型： 被转发的动态',),
                    ('separator', ),
                    *originContents,
                    *originImgs,
                ]))
            else:
                card.addCard(ResponseImage.RichContentCard([
                    ('title', '失效的动态', ),
                    ('keyword','类型： 被转发的动态',),
                    ('separator', ),
                    ('subtitle', '原动态已失效', ),
                ]))

        elif dynamicType in [2, 4]:
            # 2: 动态, 4: 直播预约
            imgs = []
            cardItem = dynamicInfo['card']['item']
            for img in cardItem.get('pictures', []):
                imgs.append(('illustration', img['img_src']))
            body = ''
            if 'description' in cardItem.keys():
                body = cardItem['description']
            elif 'content' in cardItem.keys():
                body = cardItem['content']
            elif 'title' in cardItem.keys():
                body = cardItem['title']
            addonCards = []
            for addonCard in dynamicInfo.get('display', {}).get("add_on_card_info", []):
                if 'ugc_attach_card' not in addonCard.keys(): continue
                attachCard = addonCard['ugc_attach_card']
                addonCards.append(('separator', ))
                if 'title' in attachCard.keys():
                    addonCards.append(('subtitle', attachCard['title']))
                if 'desc_second' in attachCard.keys():
                    addonCards.append(('body', attachCard['desc_second']))
                if 'play_url' in attachCard.keys():
                    addonCards.append(('body', attachCard['play_url']))
                if 'image_url' in attachCard.keys():
                    addonCards.append(('illustration', attachCard['image_url']))
            card.addCard(ResponseImage.RichContentCard([
                ('title', uname, ),
                ('subtitle',pubtime.strftime('更新于 %Y-%m-%d %H:%M:%S'), ),
                ('keyword','类型： 动态',),
                ('separator', ),
                ('body', body, ),
                *imgs,
                *addonCards,
            ]))
        elif dynamicType == 64:
            # 64: 文章
            imgs = []
            dynamicCard = dynamicInfo['card']
            for imgUrl in dynamicCard.get('image_urls', []):
                imgs.append(('illustration', imgUrl))
            contents = []
            if 'title' in dynamicCard.keys():
                contents.append(('subtitle', dynamicCard['title']))
            if 'summary' in dynamicCard.keys():
                contents.append(('body', dynamicCard['summary']))
            card.addCard(ResponseImage.RichContentCard([
                ('title', uname, ),
                ('subtitle',pubtime.strftime('更新于 %Y-%m-%d %H:%M:%S'), ),
                ('keyword','类型： 文章',),
                ('separator', ),
                *contents,
                *imgs,
            ]))
        else:
            return False, 'unsupported dynamic info type: %d'%dynamicType
        card.generateImage(savePath=savePath)
        return True, savePath
    except KeyError as e:
        return False, 'KeyError: ' + str(e)
    except BaseException as e:
        return False, 'BaseException: ' + str(e)
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

class BilibiliSubscribe(StandardPlugin):
    initGuard = Semaphore()
    def __init__(self) -> None:
        """
        self.bUps: uid -> UserFixed
        self.groupUps: group_id -> Set[uid: int]
        """
        if self.initGuard.acquire(blocking=False):
            createBilibiliTable()
        self.pattern1 = re.compile(r'^订阅\s*(\d+)$')
        self.pattern2 = re.compile(r'^取消订阅\s*(\d+)$')
        self.pattern3 = re.compile(r'^订阅$')
        self.bUps:Dict[int, BilibiliMonitor] = {}
        self.groupUps:Dict[int, Set[int]] = {}
        self._loadFromSql()
    def _loadFromSql(self)->None:
        mydb, mycursor = newSqlSession()
        mycursor.execute("""
        select group_id, uid from `bilibiliSubscribe`
        """)
        for group_id, uid in list(mycursor):
            if group_id not in self.groupUps.keys():
                self.groupUps[group_id] = set()
            if uid not in self.bUps.keys():
                self.bUps[uid] = BilibiliMonitor(uid)
            self.groupUps[group_id].add(uid)
            if group_id in APPLY_GROUP_ID:
                self.bUps[uid].addGroup(group_id)
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return self.pattern1.match(msg) != None or\
               self.pattern2.match(msg) != None or\
               self.pattern3.match(msg) != None

    def subscribeBilibili(self, group_id:int, bilibili_uid:int)->None:
        if group_id not in self.groupUps.keys():
            self.groupUps[group_id] = set()
        if bilibili_uid not in self.groupUps[group_id]:
            self.groupUps[group_id].add(bilibili_uid)
            mydb, mycursor = newSqlSession()
            mycursor.execute("""
            insert ignore into `bilibiliSubscribe` set
            group_id = %d,
            uid = %d
            """%(group_id, bilibili_uid))
        if bilibili_uid not in self.bUps.keys():
            self.bUps[bilibili_uid] = BilibiliMonitor(bilibili_uid)
        self.bUps[bilibili_uid].addGroup(group_id)
    def unsubscribeBilibili(self, group_id:int, bilibili_uid:int)->None:
        if group_id in self.groupUps.keys() and bilibili_uid in self.groupUps[group_id]:
            self.groupUps[group_id].discard(bilibili_uid)
            mydb, mycursor = newSqlSession()
            mycursor.execute("""
            delete from `bilibiliSubscribe` where
            group_id = %d and
            uid = %d
            """%(group_id, bilibili_uid))
        if bilibili_uid in self.bUps.keys():
            self.bUps[bilibili_uid].delGroup(group_id)

    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        group_id = data['group_id']
        if self.pattern1.match(msg) != None:
            uid = self.pattern1.findall(msg)[0]
            uid = int(uid)
            try:
                u = UserFixed(uid)
                userInfo = u.get_user_info()
                self.subscribeBilibili(group_id, uid)
                name = gocqQuote(userInfo['name'])
                send(group_id, f'订阅成功！\nname: {name}\nuid: {uid}')
            except ResponseCodeException as e:
                send(group_id, f'好像没找到这个UP:\n{e}')
            except KeyError as e:
                warning('bilibili api get_user_info error: {}'.format(e))
        elif self.pattern2.match(msg) != None:
            uid = self.pattern2.findall(msg)[0]
            uid = int(uid)
            self.unsubscribeBilibili(group_id, uid)
            send(group_id, '[CQ:reply,id=%d]OK'%data['message_id'])
        elif self.pattern3.match(msg) != None:
            ups = self.subscribeList(group_id)
            if len(ups) == 0:
                send(group_id, '[CQ:reply,id=%d]本群还没有订阅up哦~'%data['message_id'])
            else:
                try:
                    metas = [up.get_user_info() for up in ups]
                    metas = [f"name: {m['name']}\nuid: {m['mid']}" for m in metas]
                    send(group_id,f'本群订阅的up有：\n\n'+'\n----------\n'.join(metas))
                except BaseException as e:
                    send(group_id, 'bilibili api error')
                    warning('bilibili get_user_info error: {}'.format(e))
        return "OK"
    def onStateChange(self, nextState: bool, data: Any) -> None:
        group_id = data['group_id']
        if nextState or group_id not in self.groupUps.keys(): return
        for uid in copy.deepcopy(self.groupUps[group_id]):
            self.unsubscribeBilibili(group_id, uid)
    
    def subscribeList(self, group_id:int)->List[UserFixed]:
        uids = self.groupUps.get(group_id, set())
        return [self.bUps[uid].bUser for uid in uids]

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
class BilibiliMonitor(CronStandardPlugin):
    """bilibili up主监控类
    self.uid: 被监控的up主uid
    self.groupList
    """
    def __init__(self, uid:int) -> None:
        self.uid:int = uid
        self.bUser = UserFixed(uid=uid)
        self.groupList = set()
        self.job: Optional[Job] = None

        self.cumulativeNetworkErrCount = 0
        # _prevMeta: [prevUploadTime, prevDynamicId]
        self._prevMeta:Optional[Tuple[int, int]] = None
        self.baseInterval = 3 * 60 + random.randint(0, 100)

    def addGroup(self, group_id:int):
        self.groupList.add(group_id)
        if self.job == None:
            self.job = self.start(0, self.baseInterval)
        else:
            self.resume()
    def delGroup(self, group_id:int):
        self.groupList.discard(group_id)
        if len(self.groupList) == 0:
            self.pause()

    def tick(self) -> None:
        dynamics = None
        try:
            dynamics = self.bUser.get_dynamics(need_top=False)
        except BaseException as e:
            dynamics = None
            time.sleep(3)
        if dynamics == None: 
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
            if self.baseInterval > 120:
                self.baseInterval -= 20

        try:
            dynamicInfos = dynamics.get('cards', None)
            if dynamicInfos == None:
                return
            if len(dynamicInfos) == 0: return
            latestDynamic = dynamicInfos[0]
            uploadTime = latestDynamic['desc']['timestamp']
            isVideo = latestDynamic['desc']['type'] == 8
            dynamicId = latestDynamic['desc']['dynamic_id']
            prevMeta = self.getPrevMeta()
            if prevMeta != None and prevMeta[1] == dynamicId: return
            # 校验upload time
            if uploadTime > int(datetime.datetime.now().timestamp()):
                warning('invalid uploadTime {} in bilibili dynamic {}'.format(uploadTime, dynamicId))
                return
            if prevMeta != None and uploadTime < prevMeta[0]:
                return
            # 写入并广播
            self.writeMeta(uploadTime, dynamicId)
            author = gocqQuote(latestDynamic['desc']['user_profile']['info']['uname'])
            imgPath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'biliDynamic-%d.png'%dynamicId)
            succ, drawInfo = drawDynamicCard(latestDynamic, imgPath)
            if not succ:
                warning('draw bilibili dynamic cards failed! uid = %d, bvid = %d, reason: %s'%(self.uid, dynamicId, drawInfo))
            if isVideo:
                bvid = latestDynamic['desc']['bvid']
                for group in self.groupList:
                    send(group, f'本群订阅UP主 【{author}】 更新视频啦！\n\n链接：{bvToUrl(bvid)}')
                    if succ:
                        send(group, f'[CQ:image,file=file:///{imgPath}]')
            else:
                for group in self.groupList:
                    send(group, f'本群订阅UP主 【{author}】 更新动态啦！\n\n链接：{dynamicIdToUrl(dynamicId)}')
                    if succ:
                        send(group, f'[CQ:image,file=file:///{imgPath}]')
        except KeyError as e:
            warning('bilibili api error, uid = %d: %s'%(self.uid, str(e)))
        except BaseException as e:
            warning('base excption in BilibiliMonitor: {}'.format(e))
            self.cancel()
    def getPrevMeta(self)->Optional[Tuple[int, int]]:
        """获取该up主记录在册的前一次上传数据
        @return: Optional[(
            [0]: int: uploadTime unix时间戳
            [1]: str: dynamic_id
        )]
        """
        if self._prevMeta == None:
            mydb, mycursor = newSqlSession()
            mycursor.execute("""
            select unix_timestamp(uploadTime), `dynamicId` from `bilibiliDynamic` where
            uid = %d
            """%self.uid)
            meta = list(mycursor)
            if len(meta) != 0:
                self._prevMeta = meta[0]
        return self._prevMeta
        
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