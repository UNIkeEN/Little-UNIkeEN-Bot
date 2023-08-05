from utils.basicConfigs import ROOT_PATH, SAVE_TMP_PATH, sqlConfig
from utils.standardPlugin import StandardPlugin, NotPublishedException
from utils.basicEvent import send, warning
from typing import Dict, Union, Any, List, Tuple, Optional
import re, os.path, os
import mysql.connector
from threading import Semaphore
from .muaAPI import getTargetGroupMapping
try:
    from resources.api.muaID import TEST_MUA_TOKEN
except:
    raise NotPublishedException("TEST_MUA_TOKEN缺失，无法启用MUA插件")

def createMuaTargetSql():
    mydb = mysql.connector.connect(**sqlConfig)
    mydb.autocommit = True
    mycursor = mydb.cursor()
    mycursor.execute("""
    create table if not exists `BOT_DATA`.`muaGroupTarget` (
        `group_id` bigint unsigned not null comment '群号',
        `target` char(20) not null comment 'target MUA ID',
        primary key(`group_id`, `target`)
    )""")

def getGroupsByTarget(target:str)->List[str]:
    mydb = mysql.connector.connect(**sqlConfig)
    mydb.autocommit = True
    mycursor = mydb.cursor()
    mycursor.execute("""
    select `group_id` from `BOT_DATA`.`muaGroupTarget`
    where `target` = %s""", (target, ))
    result = list(mycursor)
    return [groupId for groupId, in result]

def getTargetsByGroup(groupId:str)->List[str]:
    mydb = mysql.connector.connect(**sqlConfig)
    mydb.autocommit = True
    mycursor = mydb.cursor()
    mycursor.execute("""
    select `target` from `BOT_DATA`.`muaGroupTarget`
    where `group_id` = %s""", (groupId,))
    result = list(mycursor)
    return [muaTarget for muaTarget, in result]

def groupBindTarget(groupId:int, muaTarget:str)->bool:
    mydb = mysql.connector.connect(**sqlConfig)
    mydb.autocommit = True
    mycursor = mydb.cursor()
    mycursor.execute("""
    replace into `BOT_DATA`.`muaGroupTarget` (`group_id`, `target`)
    values (%s, %s)""", (groupId, muaTarget))
    return True
def groupUnbindTarget(groupId:int, muaTarget:str)->Tuple[bool, str]:
    mydb = mysql.connector.connect(**sqlConfig)
    mydb.autocommit = True
    mycursor = mydb.cursor()
    mycursor.execute("""select count(*) from `BOT_DATA`.`muaGroupTarget`
    where `group_id` = %s and `target` = %s
    """, (groupId, muaTarget))
    if list(mycursor)[0][0] == 0:
        return False, '本群尚未绑定名为“%s”的MUA ID'%muaTarget
    mycursor.execute("""delete from `BOT_DATA`.`muaGroupTarget`
    where `group_id` = %s and `target` = %s
    """, (groupId, muaTarget))
    return True, '解绑成功'

class MuaGroupUnbindTarget(StandardPlugin):
    def __init__(self):
        self.triggerPattern = re.compile(r'^-muagroupunbind\s+(\S+)')
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return self.triggerPattern.match(msg) != None
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        groupId = data['group_id']
        muaTarget = self.triggerPattern.findall(msg)[0]
        succ, result = groupUnbindTarget(groupId, muaTarget)
        send(groupId, '[CQ:reply,id=%d]%s'%(data['message_id'], result))
        return 'OK'
    def getPluginInfo(self)->Any:
        return {
            'name': 'MuaGroupUnbindTarget',
            'description': '解绑群聊MUA ID',
            'commandDescription': '-muagroupunbind [MUA ID]',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': ['muaGroupTarget'],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
class MuaGroupBindTarget(StandardPlugin):
    initGuard = Semaphore()
    def __init__(self):
        if self.initGuard.acquire(blocking=False):
            createMuaTargetSql()
        self.triggerPattern = re.compile(r'^-muagroupbind\s+(\S+)')
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg.startswith('-muagroupbind')
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        groupId = data['group_id']
        if msg == '-muagroupbind':
            muaTargets = getTargetsByGroup(groupId)
            if len(muaTargets) == 0:
                send(groupId, '[CQ:reply,id=%d]当前群尚未绑定MUA ID，请输入“-muagroupbind [绑定的MUA ID]”进行target绑定'%data['message_id'])
            else:
                send(groupId, ('[CQ:reply,id=%d]当前绑定的MUAID有：%s。\n输入“-muagroupbind [绑定的MUA ID]”'
                               '可以继续绑定，输入“-muagroupunbind [绑定的MUA ID]”可以解除绑定')%(data['message_id'], '，'.join(muaTargets)))
            return 'OK'
        result = self.triggerPattern.findall(msg)
        if len(result) == 0:
            send(groupId, ('[CQ:reply,id=%d]指令识别失败。输入“-muagroupbind”可以获取群已绑定的MUAID，输入“-muagroupbind [绑定的MUA ID]”'
                           '可以继续绑定，输入“-muagroupunbind [绑定的MUA ID]可以解除绑定”')%(data['message_id'],))
        else:
            muaTarget = result[0]
            if len(muaTarget) > 20:# do some check
                send(groupId, '[CQ:reply,id=%d]绑定失败，MUA ID长度超限'%data['message_id'])
            else:
                succ = groupBindTarget(groupId, muaTarget)
                if succ:
                    send(groupId, '[CQ:reply,id=%d]绑定成功'%data['message_id'])
                else:
                    send(groupId, '[CQ:reply,id=%d]绑定失败，请联系管理员'%data['message_id'])
        return 'OK'
    def getPluginInfo(self)->Any:
        return {
            'name': 'MuaGroupBindTarget',
            'description': '绑定群聊MUA ID（通知接受对象）',
            'commandDescription': '-muagroupbind/-muagroupbind [MUA ID]',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': ['muaGroupTarget'],
            'version': '1.0.0',
            'author': 'Unicorn',
        }