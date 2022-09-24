## 鉴权与功能配置模块简介

| 模块名称 | 父类 | 触发关键词 | 触发权限| 内容 |
| ---- | ---- | ---- | ---- | ---- |
| GetPermission | StandardPlugin | '-sudo' | ROOT_ADMIN_ID | 把本人id添加到群bot管理权限名单 |
| AddPermission | StandardPlugin | '-addadmin @{某人}' | ROOT_ADMIN_ID | 把@{某人}添加到群bot管理权限名单 |
| DelPermission | StandardPlugin | '-deladmin @{某人}' | ROOT_ADMIN_ID | 把@{某人}移出群bot管理权限名单 |
| ShowPermission | StandardPlugin | '-showadmin'/'getAdmin' | None | 查看取群bot管理员权限名单 |

## 鉴权与功能配置模块示范样例

```
ROOT_ADMIN_ID = [111, # 用户A  
                 222, # 用户C
                 444] # 用户D

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

## 鉴权与功能配置模块代码分析

代码位于`plugins/getPermission.py`

TBD