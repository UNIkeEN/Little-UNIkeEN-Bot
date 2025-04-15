import os
import re
from threading import Semaphore
from typing import Any, Dict, List, Optional, Tuple, Union

from utils.basicEvent import send, warning
from utils.sqlUtils import newSqlSession
from utils.standardPlugin import StandardPlugin

from .clientInstance import queryAnnouncement
from .muaAPI import verifyMuaToken


def createMuaTokenSql():
    mydb, mycursor = newSqlSession()
    mycursor.execute("""
    create table if not exists `muaToken` (
        `user_id` bigint unsigned not null comment '用户QQ号',
        `token_description` char(20) not null comment 'MUA ID, 支持查询',
        `mua_token` varchar(100) not null comment '用户mua token, 不支持查询',
        `empowered` bool not null default false comment '是否为被授权对象',
        primary key(`user_id`, `token_description`)
    )""")

def getAllMuaToken(userId:int)->Dict[str, str]:
    mydb, mycursor = newSqlSession()
    # token_description是MUA ID
    mycursor.execute("""
    select `token_description`, `mua_token` from `muaToken` where `user_id` = %s
    """, (userId, ))
    result = {}
    for tokenDescription, muaToken in list(mycursor):
        result[tokenDescription] = muaToken
    return result

class MuaTokenBinder(StandardPlugin):
    initGuard = Semaphore()
    def __init__(self):
        self.triggerPattern = re.compile(r'^-muabind\s+(\S+)\s+(\S+)$')
        self.tokenPattern = re.compile(r'^[a-zA-Z0-9]+$')
        if self.initGuard.acquire(blocking=False):
            createMuaTokenSql()
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return self.triggerPattern.match(msg) != None
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        userId = data['user_id']
        tokenDescription, token = self.triggerPattern.findall(msg)[0]
        if len(tokenDescription) > 20:
            send(target, '[CQ:reply,id=%d]绑定失败，MUAID须在20字以内'%data['message_id'], data['message_type'])
        elif len(token) > 100 or self.tokenPattern.match(token) == None:
            send(target, '[CQ:reply,id=%d]绑定失败，请检查token格式'%data['message_id'], data['message_type'])
        else:
            try:
                succ, verifiedMuaId = verifyMuaToken(token)
                if not succ:
                    send(target, '[CQ:reply,id=%d]token验证失败，请检查token'%data['message_id'], data['message_type'])
                    return 'OK'
                if verifiedMuaId != tokenDescription:
                    send(target, '[CQ:reply,id=%d]token绑定失败，用户输入的MUA ID和服务器返回MUA ID不一致'%data['message_id'], data['message_type'])
                    return 'OK'
            except Exception as e:
                print(e)
                send(target, '[CQ:reply,id=%d]与MUA服务器连接失败，无法验证token真实性，请尝试稍后绑定'%data['message_id'], data['message_type'])
                return 'OK'
            try:
                mydb, mycursor = newSqlSession()

                mycursor.execute("""
                replace into `muaToken` (`user_id`, `token_description`, `mua_token`) values
                (%s, %s, %s)""", (userId, tokenDescription, token))
                send(target, '[CQ:reply,id=%d]绑定成功'%data['message_id'], data['message_type'])
            except BaseException as e:
                print(e)
                send(target, '[CQ:reply,id=%d]绑定失败，数据库错误'%data['message_id'], data['message_type'])
        return 'OK'
    def getPluginInfo(self)->Any:
        return {
            'name': 'MuaTokenBinder',
            'description': 'MUA token绑定',
            'commandDescription': '-muabind [UnionAPI ID] [token]',
            'usePlace': ['group', 'private'],
            'showInHelp': True,
            'pluginConfigTableNames': ['muaToken'],
            'version': '1.0.0',
            'author': 'Unicorn',
        }

# @return:  0 没有权限
#           1 使用权
#           2 拥有权
def getUserMuaIdPermission(userId:int, muaId:str)->int:
    mydb, mycursor = newSqlSession()
    mycursor.execute("""select `mua_token`, `empowered` from `muaToken` where 
    `user_id` = %s and `token_description` = %s""", (userId, muaId))
    result = list(mycursor)
    if len(result) == 0:
        return 0
    token, empowered = result[0]
    if empowered:
        return 1
    return 2

def makeEmpower(userId:int, empowerTargetId:int, muaId:str)->Tuple[bool, str]:
    mydb, mycursor = newSqlSession()
    mycursor.execute("""select `mua_token`, `empowered` from `muaToken` where 
    `user_id` = %s and `token_description` = %s""", (userId, muaId))
    result = list(mycursor)
    if len(result) == 0:
        return False, '您不存在名为“%s”的MUA ID，请输入“-muabind [MUAID] [TOKEN]”绑定之。经查询，您名下的MUA ID有：%s'%(muaId, '，'.join(getAllMuaToken(userId).keys()))
    token, empowered = result[0]
    if empowered:
        return False, '您名为“%s”的MUA ID是他人授予的，系统不支持MUA ID的递归授予，请联系MUA ID的持有者授权'%muaId
    mycursor.execute("""select count(*) from `muaToken` where 
    `user_id` = %s and `token_description` = %s""", (empowerTargetId, muaId))
    if list(mycursor)[0][0] > 0:
        return False, '您的授予对象已有名为“%s”的MUA ID了，无法绑定重名MUA ID'%muaId
    mycursor.execute("""insert into `muaToken` (`user_id`, `token_description`, `mua_token`, `empowered`)
    values (%s, %s, %s, true)""", (empowerTargetId, muaId, token))
    return True, '授权成功'

class MuaTokenEmpower(StandardPlugin):
    def __init__(self):
        self.triggerPattern1 = re.compile(r'^\-muaempower\s+(\S+)\s+(\d+)')
        self.triggerPattern2 = re.compile(r'^\-muaempower\s+(\S+)\s*\[CQ\:at\,qq=(\d+)\]')
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg.startswith('-muaempower')
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        userId = data['user_id']
        if self.triggerPattern1.match(msg) != None:
            muaId, empowerTarget = self.triggerPattern1.findall(msg)[0]
            empowerTarget = int(empowerTarget)
            succ, result = makeEmpower(userId, empowerTarget, muaId)
            send(target, '[CQ:reply,id=%d]%s'%(data['message_id'], result), data['message_type'])
        elif self.triggerPattern2.match(msg) != None:
            muaId, empowerTarget = self.triggerPattern2.findall(msg)[0]
            empowerTarget = int(empowerTarget)
            succ, result = makeEmpower(userId, empowerTarget, muaId)
            send(target, '[CQ:reply,id=%d]%s'%(data['message_id'], result), data['message_type'])
        else:
            send(target, '[CQ:reply,id=%d]指令解析错误，指令格式为“-muaempower [MUAID] [用户QQ或at用户]”，可以输入“-muaempower TEST 1234”或者“-muaempower TEST @用户1234”'%data['message_id'], data['message_type'])
        return 'OK'
    def getPluginInfo(self)->Any:
        return {
            'name': 'MuaTokenEmpower',
            'description': '授权MUA ID',
            'commandDescription': '-muaempower [MUAID] [用户QQ或at用户]',
            'usePlace': ['group', 'private'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }

class MuaTokenLister(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg == '-muals'
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        userId = data['user_id']
        tokens = getAllMuaToken(userId)
        if len(tokens) == 0:
            send(target, '[CQ:reply,id=%d]您还没有绑定mua token'%(data['message_id'], ), data['message_type'])
        else:
            result = ', '.join(tokens.keys())
            send(target, '[CQ:reply,id=%d]您的token有：%s'%(data['message_id'], result), data['message_type'])
    def getPluginInfo(self)->Any:
        return {
            'name': 'MuaTokenLister',
            'description': '列举注册的MUA ID',
            'commandDescription': '-muals',
            'usePlace': ['group', 'private'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }

class MuaTokenUnbinder(StandardPlugin):
    def __init__(self):
        self.triggerPattern = re.compile(r'^-muaunbind\s+(\S+)$')
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return self.triggerPattern.match(msg) != None
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        userId = data['user_id']
        tokenDescription = self.triggerPattern.findall(msg)[0]
        try:
            mydb, mycursor = newSqlSession()
            mycursor.execute("""
            select count(*) from `muaToken` where user_id = %s and `token_description` = %s
            """, (userId, tokenDescription))
            if list(mycursor)[0][0] == 0:
                send(target, '[CQ:reply,id=%d]您尚未绑定MUAID为 %s 的token，无法解绑'%(data['message_id'], tokenDescription), data['message_type'])
            else:
                mycursor.execute("""
                delete from `muaToken` where `user_id` = %s and `token_description` = %s
                """, (userId, tokenDescription))
                send(target, '[CQ:reply,id=%d]解绑成功'%data['message_id'], data['message_type'])
        except BaseException as e:
            print(e)
            send(target, '[CQ:reply,id=%d]解绑失败，数据库错误'%data['message_id'], data['message_type'])
        return 'OK'
    def getPluginInfo(self)->Any:
        return {
            'name': 'MuaTokenUninder',
            'description': 'MUA token解绑',
            'commandDescription': '-muaunbind [MUA ID]',
            'usePlace': ['group', 'private'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }

class MuaQuery(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg in ['-mca', 'mua通知', 'MUA通知']
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        succ, result = queryAnnouncement(data)
        send(target, result, data['message_type'])
        return 'OK'
    def getPluginInfo(self)->Any:
        return {
            'name': 'MuaQuery',
            'description': '查询MUA通知',
            'commandDescription': '-mca/mua通知',
            'usePlace': ['group', 'private'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }

class MuaAbstract(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg in ['-mcb', 'mua摘要', 'MUA摘要']
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        succ, result = queryAnnouncement(data, abstract=True)
        send(target, result, data['message_type'])
        return 'OK'
    def getPluginInfo(self)->Any:
        return {
            'name': 'MuaAbstract',
            'description': '查询MUA摘要',
            'commandDescription': '-mcb/mua摘要',
            'usePlace': ['group', 'private'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
