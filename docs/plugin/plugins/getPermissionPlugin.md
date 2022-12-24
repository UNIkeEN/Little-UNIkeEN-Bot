## 插件简介

| 插件名称 | 父类 | 触发关键词 | 触发权限| 内容 |
| ---- | ---- | ---- | ---- | ---- |
| GetPermission | StandardPlugin | '-sudo' | ROOT_ADMIN_ID | 把本人id添加到群bot管理权限名单 |
| AddPermission | StandardPlugin | '-addadmin `@{某人}`' | ROOT_ADMIN_ID | 把`@{某人}`添加到群bot管理权限名单 |
| DelPermission | StandardPlugin | '-deladmin `@{某人}`' | ROOT_ADMIN_ID | 把`@{某人}`移出群bot管理权限名单 |
| ShowPermission | StandardPlugin | '-showadmin' / 'getAdmin' | None | 查看群bot管理员权限名单 |
| AddGroupAdminToBotAdmin | StandardPlugin | '-autoconf' | ROOT_ADMIN_ID | 把群主和管理员添加进群bot管理 |

## 示范样例

代码部分：

```python
ROOT_ADMIN_ID = [111, # 用户A  
                 222, # 用户B
                 444] # 用户D
```

群聊部分：

```bash
333>>> -showadmin
bot>>> 本群管理员列表 [222, 444]

# 111自身获取权限
111>>> -sudo
bot>>> OK
777>>> -getadmin
bot>>> 本群管理员列表 [222, 444, 111]
111>>> -sudo
bot>>> 用户【111】已在管理员列表

# CQ码注入无效
111>>> -deladmin [CQ:at,qq=444]
777>>> -getadmin
bot>>> 本群管理员列表 [222, 444, 111]

# 111删除444权限
111>>> -deladmin @用户D
bot>>> OK
444>>> -getadmin
bot>>> 本群管理员列表 [111, 222]

# 444删除111权限
444>>> -deladmin @用户A
bot>>> OK
111>>> -showadmin
bot>>> 本群管理员列表 [222]
```

## 代码分析

代码位于`plugins/getPermission.py`

```python
class GetPermission(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg == '-sudo' and data['user_id'] in ROOT_ADMIN_ID and data['message_type']=='group'
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        groupId = data['group_id']
        userId = data['user_id']
        if userId not in getGroupAdmins(groupId):
            addGroupAdmin(groupId, userId)
            send(groupId, "[CQ:reply,id=%d]OK"%data['message_id'])
        else:
            send(groupId, "[CQ:reply,id=%d]用户【%d】已在管理员列表"%(data['message_id'],userId))
        return "OK"
    def getPluginInfo(self) -> dict:
        return {
            'name': 'GetPermission',
            'description': '获取群bot管理权限（仅限root使用）',
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
        userId = data['user_id']
        return self.cmdStyle.match(msg) != None and userId in ROOT_ADMIN_ID and data['message_type']=='group'
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        groupId = data['group_id']
        userId = data['user_id']
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
            'description': '添加用户群bot管理权限（仅限root使用）',
            'commandDescription': '-addadmin @{某群成员}',
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
        userId = data['user_id']
        return self.cmdStyle.match(msg) != None and userId in ROOT_ADMIN_ID and data['message_type']=='group'
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        groupId = data['group_id']
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
            'description': '删除用户群bot管理权限（仅限root使用）',
            'commandDescription': '-deladmin @{某群成员}',
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
            'description': '展示群bot管理',
            'commandDescription': '-showadmin/-getadmin',
            'usePlace': ['group'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
class AddGroupAdminToBotAdmin(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        userId = data['user_id']
        return msg in ['-autoconf', '-autoconfig'] and userId in ROOT_ADMIN_ID and data['message_type']=='group'
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        groupId = data['group_id']
        admins = set(u['user_id'] for u in get_group_member_list(groupId) if u['role'] in ['admin', 'owner']).union(
            getGroupAdmins(groupId)
        )
        setGroupAdmin(groupId, list(admins))
        send(groupId, "[CQ:reply,id=%d]OK"%data['message_id'])
        return "OK"
    def getPluginInfo(self) -> dict:
        return {
            'name': 'AddGroupAdminToBotAdmin',
            'description': '添加群主和管理为bot管理（仅限root使用）',
            'commandDescription': '-autoconf',
            'usePlace': ['group'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
```