from utils.standard_plugin import StandardPlugin
from typing import List, Any, Dict, Optional, Union, Set, Tuple
from utils.basic_event import set_group_ban, isGroupOwner, send, warning
from utils.configAPI import getGroupAdmins
from utils.basic_configs import ROOT_ADMIN_ID, SAVE_TMP_PATH, ROOT_PATH
from utils.sql_utils import newSqlSession
from utils.response_image_beta import *
from threading import Semaphore
import re, datetime

class GroupBan(StandardPlugin):
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg in ['口球我']
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        set_group_ban(data['group_id'], data['user_id'], 60)
        return "OK"
    def getPluginInfo(self) -> dict:
        return {
            'name': 'GroupBan',
            'description': '被禁言一分钟',
            'commandDescription': '口球我',
            'usePlace': ['group', ],
            'showInHelp': False,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
        
def createUserBanSql():
    mydb, mycursor = newSqlSession()
    mycursor.execute("""
    create table if not exists `userBanList`(
        `group_id` bigint unsigned not null comment '群聊id',
        `user_id` bigint unsigned not null comment '被ban者id',
        `enforcement_personnel` bigint unsigned default null comment '执法人id',
        `start_time` timestamp default null comment '执行时间',
        `end_time` timestamp default null comment '预留',
        primary key (`group_id`, `user_id`)    
    )""")
    
def loadBanList() -> Dict[int, Set[int]]:
    mydb, mycursor = newSqlSession()
    mycursor.execute("""
    select `group_id`, `user_id` from `userBanList`
    """)
    result:Dict[int, Set[int]] = {}
    for groupId, banId in list(mycursor):
        if groupId not in result.keys():
            result[groupId] = set()
        result[groupId].add(banId)
    return result

def loadGroupBanInfo(groupId:int)->List[Tuple[int, int, datetime.datetime]]:
    """
    @groupId: 群号
    @return[0]: 被ban人的qq
    @return[1]: ban人者的qq
    @return[2]: 被ban时间
    """
    mydb, mycursor = newSqlSession()
    mycursor.execute("""
    select `user_id`, `enforcement_personnel`, `start_time` from `userBanList`
    where `group_id` = %s
    """, (groupId, ))
    return list(mycursor)

class BanImplement(StandardPlugin):
    def __init__(self) -> None:
        self.banList:Dict[int, Set[int]] = {}
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return data['user_id'] in self.banList.get(data['group_id'], set())
    def executeEvent(self, msg: str, data: Any) -> Optional[str]:
        return 'OK'
    def getPluginInfo(self) -> dict:
        return {
            'name': 'BanImplement',
            'description': '机器人ban的实现插件',
            'commandDescription': 'None',
            'usePlace': ['group', ],
            'showInHelp': False,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
    def setBanList(self, banList: Dict[int, Set[int]]):
        self.banList = banList
    def addBan(self, groupId:int, banTarget:int):
        if groupId not in self.banList.keys():
            self.banList[groupId] = {banTarget, }
        else:
            self.banList[groupId].add(banTarget)
    def delBan(self, groupId:int, banTarget:int):
        if groupId in self.banList.keys():
            self.banList[groupId].discard(banTarget)
            
class UserBan(StandardPlugin):
    initGuard = Semaphore()
    def __init__(self, banImpl:BanImplement) -> None:
        if self.initGuard.acquire(blocking=False):
            createUserBanSql()
        self.banImpl = banImpl
        self.triggerPattern = re.compile(r'^\-(ban|unban)\s+(\d+|\[CQ\:at\,qq=\d+\])')
        self.cqAtPattern = re.compile(r'\[CQ\:at\,qq=(\d+)\]')
        self.banImpl.setBanList(loadBanList())
    def banUser(self, groupId:int, banId:int, data: Any):
        mydb, mycursor = newSqlSession()
        mycursor.execute("""replace into `userBanList`
        (`group_id`, `user_id`, `enforcement_personnel`, `start_time`) values 
        (%s, %s, %s, from_unixtime(%s))""",(
            groupId, banId, data['user_id'], data['time']
        ))
        self.banImpl.addBan(groupId, banId)
    def unbanUser(self, groupId:int, banId:int, data: Any):
        mydb, mycursor = newSqlSession()
        mycursor.execute("""
        delete from `userBanList` where `group_id` = %s and `user_id` = %s
        """, (groupId, banId))
        self.banImpl.delBan(groupId, banId)
    @staticmethod
    def checkBanAuthentication(banTarget:int, enforcementPersonnel:int, groupId:int)->Tuple[bool, str]:
        groupAdmins = getGroupAdmins(groupId)
        if enforcementPersonnel not in groupAdmins:
            return False, '非群BOT管理员无法使用该功能'
        if banTarget in ROOT_ADMIN_ID or isGroupOwner(group_id=groupId, user_id=banTarget):
            return False, '群主和ROOT无法被ban'
        if enforcementPersonnel in ROOT_ADMIN_ID or isGroupOwner(group_id=groupId, user_id=enforcementPersonnel):
            return True, ''
        if banTarget in groupAdmins:
            return False, '管理员不能ban管理员'
        return True, ''
    
    @staticmethod
    def checkUnbanAuthentication(banTarget:int, enforcementPersonnel:int, groupId:int)->Tuple[bool, str]:
        groupAdmins = getGroupAdmins(groupId)
        if enforcementPersonnel not in groupAdmins:
            return False, '非群BOT管理员无法使用该功能'
        else:
            return True, ''
        
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return self.triggerPattern.match(msg) != None
    def executeEvent(self, msg: str, data: Any) -> Optional[str]:
        groupId = data['group_id']
        enforcementPersonnel = data['user_id']
        banType, banTarget = self.triggerPattern.findall(msg)[0]
        if banTarget.isdigit():
            banTarget = int(banTarget)
        elif self.cqAtPattern.match(banTarget):
            banTarget = int(self.cqAtPattern.findall(banTarget)[0])
        else:
            warning('error input banTarget in UserBan: {}'.format(banTarget))
            send(groupId, '[CQ:reply,id=%d]ban失败，内部错误'%(data['message_id']))
            return
        if banType == 'ban':
            authSucc, authReason = self.checkBanAuthentication(banTarget, enforcementPersonnel, groupId)
            if authSucc:
                self.banUser(groupId, banTarget, data)
                send(groupId, '[CQ:reply,id=%d]OK'%(data['message_id']))
            else:
                send(groupId, '[CQ:reply,id=%d]%s'%(data['message_id'], authReason))
        elif banType == 'unban':
            authSucc, authReason = self.checkUnbanAuthentication(banTarget, enforcementPersonnel, groupId)
            if authSucc:
                self.unbanUser(groupId, banTarget, data)
                send(groupId, '[CQ:reply,id=%d]OK'%(data['message_id']))
            else:
                send(groupId, '[CQ:reply,id=%d]%s'%(data['message_id'], authReason))
        else:
            warning('error banType banTarget in UserBan: {}'.format(banType))
            send(groupId, '[CQ:reply,id=%d]ban失败，内部错误'%(data['message_id']))
        return 'OK'
    def getPluginInfo(self) -> dict:
        return {
            'name': 'UserBan',
            'description': '禁止/恢复用户使用机器人[🔑]',
            'commandDescription': '-ban @{...} / -unban @{...}',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': ['userBanList'],
            'version': '1.0.0',
            'author': 'Unicorn',
        }

def drawGroupBanInfo(groupId:int, groupBanInfo:List[Tuple[int, int, datetime.datetime]], savePath:str)->Tuple[bool, str]:
    card = ResponseImage(
        title='机器人ban列表',
        footer='群 %d'%groupId
    )
    if len(groupBanInfo) == 0:
        card.addCard(ResponseImage.NoticeCard(
            title='空空如也~'
        ))
    else:
        content = []
        for banTarget, enforcementPersonnel, banTime in groupBanInfo:
            content.append(('title', '被ban用户 %d, 管理员 %d, 被ban时间 %s'%(
                banTarget, enforcementPersonnel, banTime.strftime('%Y-%m-%d %H:%M:%S'))))
            content.append(('separator', ))
        card.addCard(ResponseImage.RichContentCard(content[:-1]))
    card.generateImage(savePath)
    return True, savePath

class GetBanList(StandardPlugin):
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg in ['-banlist'] and data['user_id'] in getGroupAdmins(groupId=data['group_id'])
    def executeEvent(self, msg: str, data: Any) -> Optional[str]:
        groupId = data['group_id']
        savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'banList-%d.png'%groupId)
        succ, reason = drawGroupBanInfo(groupId, loadGroupBanInfo(groupId), savePath)
        if succ:
            send(groupId, '[CQ:image,file=files:///%s]'%savePath)
        else:
            send(groupId, '[CQ:reply,id=%d]%s'%(data['message_id'], reason))
        return 'OK'
    def getPluginInfo(self) -> dict:
        return {
            'name': 'GetBanList',
            'description': '获取被ban成员名单[🔑]',
            'commandDescription': '-banlist',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }