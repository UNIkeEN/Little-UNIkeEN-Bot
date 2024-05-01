import qrcode
from utils.standardPlugin import StandardPlugin, CronStandardPlugin, Job
from utils.sqlUtils import newSqlSession
from utils.basicEvent import send, warning, gocqQuote
from utils.responseImage_beta import *
from utils.basicConfigs import ROOT_PATH, SAVE_TMP_PATH, APPLY_GROUP_ID
import re, json
from typing import List, Tuple, Optional, Union, Dict, Any, Set
#from utils.bilibili_api_fixed import UserFixed
#from bilibili_api.exceptions.ResponseCodeException import ResponseCodeException
import random
from threading import Semaphore
import copy
import time, datetime

from utils.xhs_api import UserFixed, UserNotFound



def createXhsTable()->None:
    mydb, mycursor = newSqlSession()
    mycursor.execute("""
    create table if not exists `xhsDynamic` (
        `uid` CHAR(32) not null,
        `dynamicId` CHAR(32) not null,
        `uploadTime` timestamp not null,
        primary key (`uid`)
    )""")
    mycursor.execute("""
    create table if not exists `xhsSubscribe` (
        `group_id` bigint unsigned not null,
        `uid` CHAR(32) not null,
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
            title='小红书笔记更新', primaryColor = PALETTE_RED, cardBodyFont= FONT_SYHT_M24
        )
        uname = dynamicInfo['uname']
        nid = dynamicInfo['note_id']
        

        coverLink = dynamicInfo['pic']
        qrc = qrcode.QRCode(
        version=3,
        error_correction=qrcode.constants.ERROR_CORRECT_Q,
        box_size=15,
        border=4,
        )
        qrc.add_data('https://www.xiaohongshu.com/explore/' + nid)
        qrc.make(fit=True)
        pub_date = dynamicInfo['date']
        pub_location = " 于 " + dynamicInfo['pub_location'] if dynamicInfo['pub_location'] else ''
        '''
        if (dynamicInfo['desc']):
            imgqrc = qrc.make_image(fill_color="black", back_color="transparent").convert("RGBA").resize((180,180))
            body = resizeDesciption(dynamicInfo['desc'],4,21)
            #body = dynamicInfo['desc']
            card.addCard(card.RichContentCard([
                ('title', dynamicInfo['title'], ),
                ('subtitle', uname+ "  "+pub_date + pub_location,),
                ('separator', ),
                ('illustration', coverLink,),
                ('body', body),
                
            ]))
            card_image = card.generateImage()
            card_image.paste(imgqrc, ((70),card_image.height-276),imgqrc)
            card_image.save(savePath)
        else:
            imgqrc = qrc.make_image().resize((180,180))
            card.addCard(card.RichContentCard([
                ('title', dynamicInfo['title'], ),
                ('subtitle', uname+ "  "+pub_date + pub_location,),
                ('separator', ),
                ('illustration', coverLink,),
                ('illustration', imgqrc,),
            ]))
            card.generateImage(savePath=savePath)
        '''
        imgqrc = qrc.make_image().resize((180,180))
        body = dynamicInfo['desc']
        card.addCard(card.RichContentCard([
            ('title', dynamicInfo['title'], ),
            ('subtitle', uname+ "  "+pub_date + pub_location,),
            ('separator', ),
            ('body', body),
            ('illustration', coverLink,),
            ('illustration',imgqrc,)
            
        ]))
        card_image = card.generateImage()
        card_image.save(savePath)
        return True, savePath
    
    except KeyError as e:
        return False, 'KeyError: ' + str(e)
    except BaseException as e:
        return False, 'BaseException: ' + str(e)

def resizeDesciption(raw:str, height:int, width:int)->str:
    if len(raw) == 0:
        return resizeDesciption("🍠暂无简介~", height, width)
    chunk_list = []
    num_chunk = 0
    for i in range(0, len(raw), width):
        if num_chunk == height:
            break
        chunk = raw[i:i + width]
        chunk_list.append(" "*31 +  chunk)
        num_chunk += 1

    while num_chunk < height:
        chunk_list.append(" "*31 +  "🍠")
        num_chunk += 1
    
    return "\n".join(chunk_list)


class XhsSubscribeHelper(StandardPlugin):
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg in ["小红书订阅帮助", "xhs订阅帮助"] and data['message_type']=='group'
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        group_id = data['group_id']
        send(group_id,'订阅帮助: 小红书帮助 / xhs订阅帮助\n' 
                    '订阅up:    小红书订阅 <uid>\n'
                    '取消订阅: 取消小红书订阅 <uid>\n'
                    '获取订阅列表: 小红书订阅\n'
                    '注意:  关闭本插件会自动取消所有已订阅的up')
        return "OK"
    def getPluginInfo(self) -> dict:
        return {
            'name': 'XhsSubscribeHelper',
            'description': '小红书订阅帮助',
            'commandDescription': '小红书订阅帮助',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unknown',
        }
    


class XhsSubscribe(StandardPlugin):
    initGuard = Semaphore()
    def __init__(self) -> None:
        """
        self.bUps: uid -> UserFixed
        self.groupUps: group_id -> Set[uid: int]
        """
        if self.initGuard.acquire(blocking=False):
            createXhsTable()
        #self.pattern1 = re.compile(r'^订阅\s*([0-9A-Fa-f]+)$')
        self.pattern1 = re.compile(r'^小红书订阅\s*(?:([0-9A-Fa-f]+$)|https://www\.xiaohongshu\.com/user/profile/(\S*))')

        self.pattern2 = re.compile(r'^取消小红书订阅\s*([0-9A-Fa-f]+)$')
        self.pattern3 = re.compile(r'^小红书订阅$')
        self.bUps:Dict[int, XhsMonitor] = {}
        self.groupUps:Dict[int, Set[int]] = {}
        self._loadFromSql()
    def _loadFromSql(self)->None:
        mydb, mycursor = newSqlSession()
        mycursor.execute("""
        select group_id, uid from `xhsSubscribe`
        """)
        for group_id, uid in list(mycursor):
            if group_id not in self.groupUps.keys():
                self.groupUps[group_id] = set()
            if uid not in self.bUps.keys():
                self.bUps[uid] = XhsMonitor(uid)
            self.groupUps[group_id].add(uid)
            if group_id in APPLY_GROUP_ID:
                self.bUps[uid].addGroup(group_id)
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return self.pattern1.match(msg) != None or\
               self.pattern2.match(msg) != None or\
               self.pattern3.match(msg) != None

    def subscribeXhs(self, group_id:int, xhs_uid:str)->None:
        if group_id not in self.groupUps.keys():
            self.groupUps[group_id] = set()
        if xhs_uid not in self.groupUps[group_id]:
            print(f"add {xhs_uid} into database")
            self.groupUps[group_id].add(xhs_uid)
            mydb, mycursor = newSqlSession()
            # mycursor.execute("""
            # insert into `xhsSubscribe` set
            # group_id = %d,
            # uid = '%s'
            # """%(group_id, xhs_uid))
            mycursor.execute("""
            insert into `xhsSubscribe` (group_id, uid)
            VALUES (%s, %s)
            """, (group_id, xhs_uid))

            
        if xhs_uid not in self.bUps.keys():
            self.bUps[xhs_uid] = XhsMonitor(xhs_uid)
        self.bUps[xhs_uid].addGroup(group_id)
    def unsubscribeXhs(self, group_id:int, xhs_uid:str)->None:
        if group_id in self.groupUps.keys() and xhs_uid in self.groupUps[group_id]:
            self.groupUps[group_id].discard(xhs_uid)
            mydb, mycursor = newSqlSession()
            mycursor.execute("""
            delete from `xhsSubscribe` where
            group_id = %d and
            uid = '%s'
            """%(group_id, xhs_uid))
        if xhs_uid in self.bUps.keys():
            self.bUps[xhs_uid].delGroup(group_id)

    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        group_id = data['group_id']
        if self.pattern1.match(msg) != None:
            matched_tuple = self.pattern1.findall(msg)[0]
            if (matched_tuple[0]):
                uid = matched_tuple[0]
            else:
                uid = matched_tuple[1].split("?")[0]
            #print(uid)
            try:
                u = UserFixed(uid)
                #userInfo = u.get_user_info()
                self.subscribeXhs(group_id, uid)
                #name = gocqQuote(userInfo['name'])
                name = u.get_nickname()
                send(group_id, f'订阅成功！\nname: {name}\nluid: {uid}')
            except UserNotFound as e:
                send(group_id, "用户未找到！请检查long-uid或主页url输入是否正确！")

            except KeyError as e:
                warning('xhs api get_user_info error: {}'.format(e))
        elif self.pattern2.match(msg) != None:
            uid = self.pattern2.findall(msg)[0]
            #uid = int(uid)
            self.unsubscribeXhs(group_id, uid)
            send(group_id, '[CQ:reply,id=%d]OK'%data['message_id'])
        elif self.pattern3.match(msg) != None:
            ups = self.subscribeList(group_id)
            if len(ups) == 0:
                send(group_id, '[CQ:reply,id=%d]本群还没有订阅小红书博主哦~'%data['message_id'])
            else:
                try:
                    metas = [up.get_user_info() for up in ups]
                    metas = [f"name: {m['name']}\nuid: {m['mid']}" for m in metas]
                    send(group_id,f'本群订阅的小红书博主有：\n\n'+'\n----------\n'.join(metas))
                except BaseException as e:
                    send(group_id, 'xhs api error')
                    warning('xhs get_user_info error: {}'.format(e))
        return "OK"
    def onStateChange(self, nextState: bool, data: Any) -> None:
        group_id = data['group_id']
        if nextState or group_id not in self.groupUps.keys(): return
        for uid in copy.deepcopy(self.groupUps[group_id]):
            self.unsubscribeXhs(group_id, uid)
    
    def subscribeList(self, group_id:int)->List[UserFixed]:
        uids = self.groupUps.get(group_id, set())
        return [self.bUps[uid].bUser for uid in uids]

    def getPluginInfo(self) -> dict:
        return {
            'name': 'XhsSubscribe',
            'description': '订阅小红书博主',
            'commandDescription': '小红书订阅/小红书订阅 <uid>/取消小红书订阅 <uid>',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unknown',
        }
    
class XhsMonitor(CronStandardPlugin):
    """Xhs 博主监控类
    self.luid: 被监控的up主luid
    self.groupList
    """
    def __init__(self, luid:int) -> None:
        self.luid:int = luid
        self.bUser = UserFixed(luid=luid)
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
            dynamicInfos = dynamics
            if dynamicInfos == None:
                return
            if len(dynamicInfos) == 0: return

            
            latestDynamic = dynamicInfos[0]
            #print(f"last dy is {latestDynamic}")
            uploadTime = latestDynamic['timestp']
            #isVideo = latestDynamic['desc']['type'] == 8
            dynamicId = latestDynamic['note_id']
            
            prevMeta = self.getPrevMeta()
            if prevMeta != None and prevMeta[1] == dynamicId: return
            # 校验upload time
            if uploadTime > int(datetime.datetime.now().timestamp()):
                warning('invalid uploadTime {} in xhs dynamic {}'.format(uploadTime, dynamicId))
                return
            if prevMeta != None and uploadTime < prevMeta[0]:
                return
            

            # 写入并广播
            self.writeMeta(uploadTime, dynamicId)
            author = gocqQuote(latestDynamic['uname'])
            imgPath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'xhsDynamic-%s.png'%dynamicId)

            succ, drawInfo = drawDynamicCard(latestDynamic, imgPath)
            if not succ:
                warning('draw xhs dynamic cards failed! luid = %s, bvid = %s, reason: %s'%(self.luid, dynamicId, drawInfo))
            
            ## 图文or视频
            for group in self.groupList:
                    url = 'https://www.xiaohongshu.com/explore/' + latestDynamic['note_id']
                    send(group, f'本群订阅小红书博主 【{author}】 更新笔记啦！\n\n链接：{url}')
                    if succ:
                        send(group, f'[CQ:image,file=file:///{imgPath}]')
            
        except KeyError as e:
            warning('xhs api error, luid = %d: %s'%(self.luid, str(e)))
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
            # mycursor.execute("""
            # select unix_timestamp(uploadTime), `dynamicId` from `xhsDynamic` where
            # uid = '%s'   
            # """%self.luid) #大坑！ 字符串必须加单引号！
            mycursor.execute("""
            select unix_timestamp(uploadTime), `dynamicId` from `xhsDynamic` where
            uid = %s   
            """,(self.luid,)) 
            meta = list(mycursor)
            if len(meta) != 0:
                self._prevMeta = meta[0]
        return self._prevMeta
        
    def writeMeta(self, uploadTime:int, dynamicId:int)->None:
        """写入up主本次上传数据"""
        meta = (uploadTime, dynamicId)
        self._prevMeta = meta
        mydb, mycursor = newSqlSession()
        print(uploadTime, dynamicId, self.luid)
        mycursor.execute("""
        replace into `xhsDynamic` set
        uploadTime = from_unixtime(%s),
        dynamicId = %s,
        uid = %s
        """, (uploadTime, dynamicId, self.luid))

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

