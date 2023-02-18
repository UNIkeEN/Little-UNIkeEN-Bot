# bot 管理 API

## 1. 介绍

| 函数名 | 参数 | 返回值 | 功能 | 代码位置 |
| ---- | ---- | ---- | ---- | ---- |
| createGlobalConfig | - | `None` | 创建用于记录群bot管理和插件开关情况的sql表 | `utils.basicConfigs` |
| readGlobalConfig | `@groupId`: 群号, `int`或`None`类型<br>`@pluginName`: 插件名称, `str`类型 | config值, `Union[dict,Any,None]`类型 | 读取`BOT_DATA.globalConfig`:<br>如果`@groupId`是`None`, 那么读取所有群的config, 并返回`Dict[群号, config]`<br>如果`@groupId`是`int`, 那么读取对应群的config, 并返回`Any`<br>其余情况warning并返回`None` | `utils.basicConfigs` |
| writeGlobalConfig | `@groupId`: 群号, `int`或`None`类型<br>`@pluginName`: 插件名称, `str`类型<br>`@value`: 要写入的值, 可json化的`Any`类型 | `None` | 写入`BOT_DATA.globalConfig`:<br>如果`@groupId`是`None`, 那么写所有群的config<br>如果`@groupId`是`int`, 那么写对应群的config<br>其余情况warning | `utils.basicConfigs` |
| getPluginEnabledGroups | `@pluginName`: 插件名称, `str`类型 | 开启插件的群列表, `List[int]`类型 | 获取开启插件的群聊id列表 | `utils.basicConfigs` |
| getGroupAdmins | `@groupId`: 群号, `int`类型 | 群bot管理的qq号列表, `List[int]`类型 | 获取群bot管理列表 | `utils.basicConfigs` |
| addGroupAdmin | `@groupId`: 群号, `int`类型<br>`@adminId`: 待添加的qq号, `int`类型 | `None` | 把某个qq添加到群bot管理 | `utils.basicConfigs` |
| setGroupAdmin | `@groupId`: 群号, `int`类型<br>`@adminIds`: 设定的qq号列表, `List[int]`类型 | 设置群bot管理列表设为给定list | `utils.basicConfigs` |
| delGroupAdmin | `@groupId`: 群号, `int`类型<br>`@adminId`: 待删除的qq号, `int`类型 | `None` | 把某qq号从群bot管理列表中删除 | `utils.basicConfigs` |

## 2. 样例分析

```python
# 1. 初始化值
groupId = 12345

# 2. 把群groupId的superemoji插件打开
writeGlobalConfig(groupId, 'superemoji.enable', True)
```

## 3. 代码分析

代码位于 `utils.basicConfigs`

```python
def createGlobalConfig():
    """创建global config的sql table, 移除不在APPLY_GROUP_ID中的群号"""
    mydb = mysql.connector.connect(**sqlConfig)
    mycursor = mydb.cursor()
    mydb.autocommit = True
    mycursor.execute("""
    create database if not exists `BOT_DATA`
    """)
    mycursor.execute("""
    create table if not exists `BOT_DATA`.`globalConfig` (
        `groupId` bigint not null,
        `groupConfig` json,
        `groupAdmins` json,
        primary key (`groupId`)
    );""")
    mycursor.execute("select groupId from BOT_DATA.globalConfig")
    groupNeedToBeRemoved = set([x for x, in list(mycursor)]) - set(APPLY_GROUP_ID)
    for groupId in groupNeedToBeRemoved:
        mycursor.execute("delete from BOT_DATA.globalConfig where groupId = %d"%groupId)

def readGlobalConfig(groupId: Union[None, int], pluginName: str)->Union[dict, Any, None]:
    """读global config
    @groupId
        if None, then read add groups config
        elif int, read the specific group config
        else: warning
    @pluginName
        like 'test1.enable' or 'test1'
    """
    mydb = mysql.connector.connect(**sqlConfig)
    mycursor = mydb.cursor()
    pluginName = escape_string(pluginName)
    if groupId == None:
        result = {}
        try:
            mycursor.execute("SELECT groupId, json_extract(groupConfig,'$.%s') from BOT_DATA.globalConfig"%pluginName)
        except mysql.connector.Error as e:
            warning("error in readGlobalConfig: {}".format(e))
            return None
        for grpId, groupConfig in list(mycursor):
            if groupConfig != None:
                result[grpId] = json.loads(groupConfig)
        return result
    elif isinstance(groupId, int):
        result = {}
        try:
            mycursor.execute("SELECT groupId, json_extract(groupConfig, '$.%s') from BOT_DATA.globalConfig where groupId = %d"%(pluginName, groupId))
        except mysql.connector.Error as e:
            warning("error in readGlobalConfig: {}".format(e))
            return None
        for grpId, groupConfig in list(mycursor):
            if groupConfig != None:
                result[grpId] = json.loads(groupConfig)
        if len(result) == 0:
            return None
        else:
            return result[groupId]
    else:
        warning("unknow groupId type in readGlobalConfig: groupId = {}".format(groupId))
        return None
# update BOT_DATA.test set groupConfig=json_set(groupConfig, '$.test1.enable', False) where groupId=1234;
def writeGlobalConfig(groupId: Union[None, int], pluginName: str, value: Any):
    """写global config
    @groupId
        if None, then write all groups' config
        elif int, write the specific group config
        else: warning
    @pluginName
        like 'test1.enable' or 'test1'
    @value
    """
    mydb = mysql.connector.connect(**sqlConfig)
    mycursor = mydb.cursor()
    pluginName = escape_string(pluginName)
    if groupId == None:
        try:
            mycursor.execute("update BOT_DATA.globalConfig set groupConfig=json_set(groupConfig, '$.%s', cast('%s' as json))"%(pluginName, json.dumps(value)))
        except mysql.connector.Error as e:
            warning("error in writeGlobalConfig: {}".format(e))
    elif isinstance(groupId, int):
        try:
            mycursor.execute("insert ignore into BOT_DATA.globalConfig(groupId, groupConfig, groupAdmins) values (%d, '{}', '[]')"%groupId)
            mycursor.execute("update BOT_DATA.globalConfig set groupConfig=json_set(groupConfig, '$.%s', cast('%s' as json)) where groupId=%d"%(pluginName, json.dumps(value), groupId))
        except mysql.connector.Error as e:
            warning("mysql error in writeGlobalConfig: {}".format(e))
    else:
        warning("unknow groupId type in writeGlobalConfig: groupId = {}".format(groupId))
    mydb.commit()

def getPluginEnabledGroups(pluginName: str)->List[int]:
    """获取开启插件的群聊id列表
    @pluginName: 被pluginGroupManager管理的插件组名称
        eg: "faq", "superemoji"

    @return: 开启插件的群id列表
    """
    mydb = mysql.connector.connect(**sqlConfig)
    mycursor = mydb.cursor()
    pluginName = escape_string(pluginName)
    try:
        mycursor.execute("select groupId from BOT_DATA.globalConfig \
            where json_extract(groupConfig, '$.%s.enable') = true"%escape_string(pluginName))
        return [x[0] for x in list(mycursor)]
    except mysql.connector.Error as e:
        warning("mysql error in getPluginEnabledGroups: {}".format(e))

def getGroupAdmins(groupId: int)->List[int]:
    """获取群bot管理列表
    @groupId: 群号
    @return:  群bot管理员QQ号列表
    """
    mydb = mysql.connector.connect(**sqlConfig)
    mycursor = mydb.cursor()
    try:
        mycursor.execute("select groupAdmins from BOT_DATA.globalConfig where groupId = %s"%(groupId))
        result = list(mycursor)
        if len(result) <= 0:
            mycursor.execute("insert ignore into BOT_DATA.globalConfig(groupId, groupConfig, groupAdmins) values (%d, '{}', '[]')"%groupId)
            mydb.commit()
            return []
        else:
            result = json.loads(result[0][0])
            if not isinstance(result, list) or any([not isinstance(x, int) for x in result]):
                warning('error admin type, groupId = %d'%groupId)
                return []
            return result
    except mysql.connector.Error as e:
        warning("error in getGroupAdmins: {}".format(e))
        return []

def addGroupAdmin(groupId: int, adminId: int):
    """添加群bot管理
    @groupId: 群号
    @adminId: 新添加的群bot管理员QQ号
    """
    if not isinstance(groupId, int) or not isinstance(adminId, int):
        warning("error groupId type or adminId type in addGroupAdmin: groupId = {}, adminId = {}".format(groupId, adminId))
        return
    mydb = mysql.connector.connect(**sqlConfig)
    mycursor = mydb.cursor()
    try:
        mycursor.execute("insert ignore into BOT_DATA.globalConfig(groupId, groupConfig, groupAdmins) values (%d, '{}', '[]')"%groupId)
        mycursor.execute("update BOT_DATA.globalConfig set groupAdmins=json_array_append(groupAdmins,'$', %d) where groupId=%d;"%(adminId, groupId))
        mydb.commit()
    except mysql.connector.Error as e:
        warning("error in addGroupAdmin: {}".format(e))
def setGroupAdmin(groupId: int, adminIds: List[int]):
    """设置群bot管理为某个list
    @groupId: 群号
    @adminIds: 更改后的群bot管理员QQ号列表
    """
    if not isinstance(adminIds, list) or any([not isinstance(x, int) for x in adminIds]):
        warning('error admin type, groupId = %d'%groupId)
        return
    mydb = mysql.connector.connect(**sqlConfig)
    mycursor = mydb.cursor()
    try:
        mycursor.execute("insert ignore into BOT_DATA.globalConfig(groupId, groupConfig, groupAdmins) values (%d, '{}', '[]')"%groupId)
        mycursor.execute("update BOT_DATA.globalConfig set groupAdmins='%s' where groupId=%d;"%(json.dumps(adminIds), groupId))
        mydb.commit()
    except mysql.connector.Error as e:
        warning("error in setGroupAdmin: {}".format(e))
def delGroupAdmin(groupId: int, adminId: int):
    """删除群bot管理员
    @groupId: 群号
    @adminId: 要删除的群bot管理员QQ号
    """
    if not isinstance(groupId, int) or not isinstance(adminId, int):
        warning("error groupId type or adminId type in delGroupAdmin: groupId = {}, adminId = {}".format(groupId, adminId))
        return
    groupAdmins = getGroupAdmins(groupId)
    if groupAdmins == None:
        warning("groupAdmins is None at delGroupAdmin")
        return
    groupAdmins = set(groupAdmins)
    if adminId not in groupAdmins:
        warning("id = '%d' not in admins at delGroupAdmin"%adminId)
        return
    groupAdmins.remove(adminId)
    setGroupAdmin(groupId, list(groupAdmins))
```