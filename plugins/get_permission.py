from typing import Union, Any
from utils.configAPI import delGroupAdmin, addGroupAdmin, setGroupAdmin, getGroupAdmins
from utils.basic_event import send, get_group_member_list, isGroupOwner
from utils.basic_configs import ROOT_ADMIN_ID
from utils.standard_plugin import StandardPlugin
import re
class GetPermission(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg == '-sudo' and data['message_type']=='group'
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        groupId = data['group_id']
        userId = data['user_id']
        if userId not in ROOT_ADMIN_ID and not isGroupOwner(group_id=groupId, user_id=userId):
            send(groupId, "[CQ:reply,id=%d]无权限"%data['message_id'])
            return 'OK'
        if userId not in getGroupAdmins(groupId):
            addGroupAdmin(groupId, userId)
            send(groupId, "[CQ:reply,id=%d]OK"%data['message_id'])
        else:
            send(groupId, "[CQ:reply,id=%d]用户【%d】已在管理员列表"%(data['message_id'],userId))
        return "OK"
    def getPluginInfo(self) -> dict:
        return {
            'name': 'GetPermission',
            'description': '获取🔑权限[👑🔒]',
            'commandDescription': '-sudo',
            'usePlace': ['group'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
class AddPermission(StandardPlugin):
    def __init__(self) -> None:
        self.cmdStyle = re.compile(r'^-addadmin ?\[CQ:at,qq=(\d+)\]$')
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return self.cmdStyle.match(msg) != None and data['message_type']=='group'
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        groupId = data['group_id']
        userId = data['user_id']
        if userId not in ROOT_ADMIN_ID and not isGroupOwner(group_id=groupId, user_id=userId):
            send(groupId, "[CQ:reply,id=%d]无权限"%data['message_id'])
            return 'OK'
        targetId = int(self.cmdStyle.findall(msg)[0])
        print(getGroupAdmins(groupId))
        if targetId not in getGroupAdmins(groupId):
            addGroupAdmin(groupId, targetId)
            send(groupId, "[CQ:reply,id=%d]OK"%data['message_id'])
        else:
            send(groupId, "用户【%d】已在管理员列表"%targetId)
        return "OK"
    def getPluginInfo(self) -> dict:
        return {
            'name': 'AddPermission',
            'description': '添加🔑权限[👑🔒]',
            'commandDescription': '-addadmin @{..}',
            'usePlace': ['group'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
class DelPermission(StandardPlugin):
    def __init__(self) -> None:
        self.cmdStyle = re.compile(r'^-deladmin ?\[CQ:at,qq=(\d+)\]$')
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return self.cmdStyle.match(msg) != None and data['message_type']=='group'
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        userId = data['user_id']
        groupId = data['group_id']
        if userId not in ROOT_ADMIN_ID and not isGroupOwner(group_id=groupId, user_id=userId):
            send(groupId, "[CQ:reply,id=%d]无权限"%data['message_id'])
            return 'OK'
        targetId = int(self.cmdStyle.findall(msg)[0])
        if targetId in getGroupAdmins(groupId):
            delGroupAdmin(groupId, targetId)
            send(groupId, "[CQ:reply,id=%d]OK"%data['message_id'])
        else:
            send(groupId, "用户【%d】不在管理员列表"%targetId)
        return "OK"
    def getPluginInfo(self) -> dict:
        return {
            'name': 'DelPermission',
            'description': '删除🔑权限[👑🔒]',
            'commandDescription': '-deladmin @{..}',
            'usePlace': ['group'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
class ShowPermission(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg in ['-showadmin', '-getadmin'] and data['message_type']=='group'
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        groupId = data['group_id']
        admins = getGroupAdmins(groupId)
        send(groupId, '[CQ:reply,id={}]本群管理员列表 {}'.format(data['message_id'], admins))
        return "OK"
    def getPluginInfo(self) -> dict:
        return {
            'name': 'ShowPermission',
            'description': '展示🔑权限拥有者',
            'commandDescription': '-showadmin/-getadmin',
            'usePlace': ['group'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
class AddGroupAdminToBotAdmin(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg in ['-autoconf', '-autoconfig'] and data['message_type']=='group'
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        groupId = data['group_id']
        userId = data['user_id']
        if userId not in ROOT_ADMIN_ID and not isGroupOwner(group_id=groupId, user_id=userId):
            send(groupId, "[CQ:reply,id=%d]无权限"%data['message_id'])
            return 'OK'
        admins = set(u['user_id'] for u in get_group_member_list(groupId) if u['role'] in ['admin', 'owner']).union(
            getGroupAdmins(groupId)
        )
        setGroupAdmin(groupId, list(admins))
        send(groupId, "[CQ:reply,id=%d]OK"%data['message_id'])
        return "OK"
    def getPluginInfo(self) -> dict:
        return {
            'name': 'AddGroupAdminToBotAdmin',
            'description': '注册群主和群管为🔑[👑🔒]',
            'commandDescription': '-autoconf',
            'usePlace': ['group'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }