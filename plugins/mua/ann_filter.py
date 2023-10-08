from utils.basic_event import send, get_group_member_list
from utils.standard_plugin import StandardPlugin
from utils.configAPI import getGroupAdmins
from utils.sql_utils import newSqlSession
from threading import Semaphore
import json
import re
from typing import Any, Optional, Dict, List, Tuple, Union, Set

from .mua_targets import getTargetsByGroup

class AnnouncementFilter:
    class ThingFilter:
        def apply(self, thing : Any) -> bool:
            raise NotImplementedError()

        @staticmethod
        def asSet(thing : Any)->Set[Any]:
            if isinstance(thing, set):
                return thing
            if isinstance(thing, list):
                return set(thing)
            return set([thing])

        def dump(self) -> str:
            raise NotImplementedError()

    class BlackList(ThingFilter):
        def __init__(self, blacklist : Union[None, List[Any]]):
            self.blacklist = set(blacklist) if blacklist is not None else None
        
        def apply(self, thing : Any) -> bool:
            if thing is None:
                return True
            if self.blacklist is None:
                return True
            thing:Set[Any] = AnnouncementFilter.ThingFilter.asSet(thing)
            return thing.issubset(self.blacklist)

    class WhiteList(ThingFilter):
        def __init__(self, whitelist : Union[None, List[Any]]):
            self.whitelist = set(whitelist) if whitelist is not None else None
        
        def apply(self, thing : Any) -> bool:
            if thing is None:
                return True
            if self.whitelist is None:
                return True
            thing = AnnouncementFilter.ThingFilter.asSet(thing)
            return not thing.isdisjoint(self.whitelist)

    def __init__(self, muaIds : Union[None, List[str]], filterJsonStr : Union[None, str]):
        self.targetFilter = AnnouncementFilter.WhiteList(muaIds)
        if filterJsonStr is None or filterJsonStr.strip() == '':
            self.channelFilter = AnnouncementFilter.WhiteList(None)
        else:
            filterJson = json.loads(filterJsonStr)
            self.channelFilter = AnnouncementFilter.makeFilter(filterJson['channel'])

    def apply(self, ann : Dict[str, Any]) -> bool:
        targets = ann.get('targets', None)
        channel = ann['channel']
        return self.targetFilter.apply(targets) and self.channelFilter.apply(channel)

    @staticmethod
    def makeFilter(obj: Dict[str, List[str]]) -> ThingFilter:
        if 'whitelist' in obj:
            return AnnouncementFilter.WhiteList(obj['whitelist'])
        elif 'blacklist' in obj:
            return AnnouncementFilter.BlackList(obj['blacklist'])
        else:
            return AnnouncementFilter.WhiteList(None)

    @staticmethod
    def parseAsFilterJson(filterStr: str) -> Tuple[bool, Union[None, str]]:
        if filterStr.startswith('channel+:'):
            whitelist = filterStr[9:].strip().split()
            return True, json.dumps({
                'channel' : {
                    'whitelist' : whitelist
                }
            })
        elif filterStr.startswith('channel-:'):
            blacklist = filterStr[9:].strip().split()
            return True, json.dumps({
                'channel' : {
                    'blacklist' : blacklist
                }
            })
        else:
            return False, None

def createMuaGroupAnnFilterSql():
    mydb, mycursor = newSqlSession()
    mycursor.execute("""
    create table if not exists `muaGroupAnnFilter` (
        `group_id` bigint unsigned not null comment '群号',
        `filter` varchar(500) default null comment '过滤器json',
        primary key(`group_id`)
    )""")

def getGroupFilter(groupId:str)->AnnouncementFilter:
    mydb, mycursor = newSqlSession()
    mycursor.execute("""
    select `filter` from `muaGroupAnnFilter`
    where `group_id` = %s""", (groupId,))
    result = list(mycursor)
    if len(result) > 0:
        result = result[0][0]
    else:
        result = None
    return AnnouncementFilter(getTargetsByGroup(groupId), result)

def setGroupFilter(groupId:int, filterStr:str)->bool:
    mydb, mycursor = newSqlSession()
    succ, filterJsonStr = AnnouncementFilter.parseAsFilterJson(filterStr)
    if succ:
        mycursor.execute("""
        replace into `muaGroupAnnFilter` (`group_id`, `filter`)
        values (%s, %s)""", (groupId, filterJsonStr))
        return True
    return False

def rmGroupFilter(groupId:int)->bool:
    mydb, mycursor = newSqlSession()
    mycursor.execute("""select count(*) from `muaGroupAnnFilter`
    where `group_id` = %s
    """, (groupId,))
    if list(mycursor)[0][0] == 0:
        return False
    mycursor.execute("""delete from `muaGroupAnnFilter`
    where `group_id` = %s
    """, (groupId,))
    return True

class MuaGroupAnnFilter(StandardPlugin):
    initGuard = Semaphore()
    def __init__(self):
        if self.initGuard.acquire(blocking=False):
            createMuaGroupAnnFilterSql()
        self.triggerPattern = re.compile(r'^-setannfilter\s+(\S+)')
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg.startswith('-setannfilter') or msg.startswith('-rmannfilter')
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        groupId = data['group_id']
        userId = data['user_id']
        admins = set(u['user_id'] for u in get_group_member_list(groupId) if u['role'] in ['admin', 'owner']).union(
            getGroupAdmins(groupId)
        )
        if userId not in admins:
            send(groupId, '[CQ:reply,id=%d]权限检查失败。该指令仅允许群管理员触发。'%data['message_id'], data['message_type'])
            return 'OK'
        if msg == '-rmannfilter':
            if not rmGroupFilter(groupId):
                send(groupId, '[CQ:reply,id=%d]没有设置过订阅频道。'%data['message_id'], data['message_type'])
            else:
                send(groupId, '[CQ:reply,id=%d]删除成功。'%data['message_id'], data['message_type'])
            return 'OK'
        result = self.triggerPattern.findall(msg)
        if len(result) > 0:
            filterStr = result[0]
            succ = setGroupFilter(groupId, filterStr)
            if succ:
                send(groupId, '[CQ:reply,id=%d]设置成功'%data['message_id'])
                return 'OK'
        send(groupId, ('[CQ:reply,id=%d]指令识别失败。输入“-setannfilter channel+:xxx xxx”设置订阅的频道白名单；输入“-setannfilter channel-:xxx xxx”'
                        '设置黑名单；“-rmannfilter”重置为默认状态。')%(data['message_id'],))
        return 'OK'
    def getPluginInfo(self)->Any:
        return {
            'name': 'MuaGroupAnnFilter',
            'description': '设置群聊订阅的MUA通知频道',
            'commandDescription': '-setannfilter channel+/channel-:xxx xxx || -rmannfilter',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': ['muaGroupAnnFilter'],
            'version': '1.0.0',
            'author': 'Unicorn',
        }