from typing import Union, Any
from utils.basicEvent import delGroupAdmin, send, addGroupAdmin, getGroupAdmins
from utils.basicConfigs import ROOT_ADMIN_ID
from utils.standardPlugin import StandardPlugin
import re
class GetPermission(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg == '-sudo' and data['user_id'] in ROOT_ADMIN_ID
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        groupId = data['group_id']
        userId = data['user_id']
        if userId not in getGroupAdmins(groupId):
            addGroupAdmin(groupId, userId)
            send(groupId, "OK")
        else:
            send(groupId, "用户【%d】已在管理员列表"%userId)
        return "OK"
    def getPluginInfo(self) -> dict:
        return {
            'name': 'GetPermission',
            'description': '获取群bot管理权限（仅限root使用）',
            'commandDescription': '-sudo',
            'usePlace': ['group'],
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
class AddPermission(StandardPlugin):
    def __init__(self) -> None:
        self.cmdStyle = re.compile(r'^-addadmin ?\[CQ:at,qq=(\d+)\]$')
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        userId = data['user_id']
        return self.cmdStyle.match(msg) != None and userId in ROOT_ADMIN_ID
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        groupId = data['group_id']
        userId = data['user_id']
        targetId = int(self.cmdStyle.findall(msg)[0])
        print(getGroupAdmins(groupId))
        if targetId not in getGroupAdmins(groupId):
            addGroupAdmin(groupId, targetId)
            send(groupId, "OK")
        else:
            send(groupId, "用户【%d】已在管理员列表"%targetId)
        return "OK"
    def getPluginInfo(self) -> dict:
        return {
            'name': 'AddPermission',
            'description': '添加用户群bot管理权限（仅限root使用）',
            'commandDescription': '-addadmin @{某群成员}',
            'usePlace': ['group'],
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
class DelPermission(StandardPlugin):
    def __init__(self) -> None:
        self.cmdStyle = re.compile(r'^-deladmin ?\[CQ:at,qq=(\d+)\]$')
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        userId = data['user_id']
        return self.cmdStyle.match(msg) != None and userId in ROOT_ADMIN_ID
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        groupId = data['group_id']
        targetId = int(self.cmdStyle.findall(msg)[0])
        if targetId in getGroupAdmins(groupId):
            delGroupAdmin(groupId, targetId)
            send(groupId, "OK")
        else:
            send(groupId, "用户【%d】不在管理员列表"%targetId)
        return "OK"
    def getPluginInfo(self) -> dict:
        return {
            'name': 'DelPermission',
            'description': '删除用户群bot管理权限（仅限root使用）',
            'commandDescription': '-deladmin @{某群成员}',
            'usePlace': ['group'],
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
class ShowPermission(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg in ['-showadmin', '-getadmin']
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        groupId = data['group_id']
        admins = getGroupAdmins(groupId)
        send(groupId, '本群管理员列表 {}'.format(admins))
        return "OK"
    def getPluginInfo(self) -> dict:
        return {
            'name': 'ShowPermission',
            'description': '展示群bot管理',
            'commandDescription': '-showadmin/-getadmin',
            'usePlace': ['group'],
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }