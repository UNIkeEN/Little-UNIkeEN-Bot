from typing import Dict, Union, Any, List, Tuple, Optional
from utils.basicEvent import send, warning
from utils.configAPI import getGroupAdmins
from utils.standardPlugin import StandardPlugin
from utils.basicConfigs import ROOT_PATH, SAVE_TMP_PATH, sqlConfig
from utils.responseImage_beta import PALETTE_RED, ResponseImage, PALETTE_CYAN, FONTS_PATH, ImageFont
import re, os.path, os
from pypinyin import lazy_pinyin
import mysql.connector
from threading import Semaphore

def createMuaTokenSql():
    mydb = mysql.connector.connect(**sqlConfig)
    mydb.autocommit = True
    mycursor = mydb.cursor()
    mycursor.execute("""
    create table if not exists `BOT_DATA`.`muaToken` (
        `user_id` bigint unsigned not null comment '用户QQ号',
        `token_description` char(20) not null comment 'token描述',
        `mua_token` varchar(100) not null comment '用户mua token',
        primary key(`user_id`, `token_description`)
    )""")

def getAllMuaToken(userId:int)->Dict[str, str]:
    mydb = mysql.connector.connect(**sqlConfig)
    mydb.autocommit = True
    mycursor = mydb.cursor()
    mycursor.execute("""
    select `token_description`, `mua_token` from `BOT_DATA`.`muaToken` where `user_id` = %s
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
            send(target, '[CQ:reply,id=%d]绑定失败，token描述符须在20字以内'%data['message_id'], data['message_type'])
        elif len(token) > 100 or self.tokenPattern.match(token) == None:
            send(target, '[CQ:reply,id=%d]绑定失败，请检查token格式'%data['message_id'], data['message_type'])
        else:
            try:
                mydb = mysql.connector.connect(**sqlConfig)
                mydb.autocommit = True
                mycursor = mydb.cursor()
                mycursor.execute("""
                replace into `BOT_DATA`.`muaToken` (`user_id`, `token_description`, `mua_token`) values
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
            'commandDescription': '-muabind [token描述符(无空格和换行)] [token]',
            'usePlace': ['group', 'private'],
            'showInHelp': True,
            'pluginConfigTableNames': ['muaToken'],
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
            'description': 'MUA token列举',
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
            mydb = mysql.connector.connect(**sqlConfig)
            mydb.autocommit = True
            mycursor = mydb.cursor()
            mycursor.execute("""
            select count(*) from `BOT_DATA`.`muaToken` where user_id = %s and `token_description` = %s
            """, (userId, tokenDescription))
            if list(mycursor)[0][0] == 0:
                send(target, '[CQ:reply,id=%d]您尚未绑定描述符为 %s 的token，无法解绑'%(data['message_id'], tokenDescription), data['message_type'])
            else:
                mycursor.execute("""
                delete from `BOT_DATA`.`muaToken` where `user_id` = %s and `token_description` = %s
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
            'commandDescription': '-muaunbind [token描述符]',
            'usePlace': ['group', 'private'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }