## 插件简介

| 插件名称 | 父类 | 触发关键词 | 触发权限| 内容 |
| ---- | ---- | ---- | ---- | ---- |
| PluginGroupManager | StandardPlugin | ... | ... | ... |

## 具体介绍

PluginGroupManager具有两个功能：

1. 作为插件管理者，接收 `re.compile('-grpcfg (enable|disable) %s'%groupName)` 型参数，作为开启或关闭插件组的指令，此功能需要群bot管理权限
2. 作为中间平台，接收输入传给被管理对象，检测被管理对象是否能接收参数并运行

您可以把数个插件类对象放进列表，然后传给PluginGroupManager作为构造函数的第一个参数，groupName作为第二个参数传给构造函数，如下面示范样例

## 示范样例

代码部分：

```python
ROOT_ADMIN_ID = [111, # 用户A  
                 222, # 用户B
                 444] # 用户D
from plugins.superEmoji import FireworksFace, FirecrackersFace, BasketballFace, HotFace

GroupPluginList = [
    # .....
    PluginGroupManager([FireworksFace(), FirecrackersFace(), BasketballFace(), HotFace()], 'superemoji'),
    # .....
]
```

群聊部分：

```bash
# 群内尚未开启super emoji功能
111> 热死了
# bot不予理会

# 111开启群super emoji功能
111> -sudo
bot> OK
111> -grpcfg enable superemoji
bot> OK

# 开始互动
222> 篮球
bot> 【超级表情：篮球】

# 111关闭群super emoji功能
111> -grpcfg disable superemoji
bot> OK

# 444尝试互动
444> 篮球
# bot不予理会
```

## 代码分析

代码位于`utils/standardPlugin.py`

```python
from utils.basicEvent import send, warning, readGlobalConfig, writeGlobalConfig, getGroupAdmins

class PluginGroupManager(StandardPlugin):
    def __init__(self, plugins:List[StandardPlugin], groupName: str) -> None:
        self.plugins = plugins
        self.groupName = groupName
        self.readyPlugin = None
        self.enabledDict = readGlobalConfig(None, groupName+'.enable')
        self.defaultEnabled = False
    def judgeTrigger(self, msg:str, data:Any)->bool:
        userId = data['user_id']
        groupId = data['group_id']
        if msg == '-grpcfg enable %s'%self.groupName and userId in getGroupAdmins(groupId):
            self.readyPlugin = 'enable'
            return True
        if msg == '-grpcfg disable %s'%self.groupName and userId in getGroupAdmins(groupId):
            self.readyPlugin = 'disable'
            return True
        if not self.queryEnabled(groupId):
            return False
        for plugin in self.plugins:
            if plugin.judgeTrigger(msg, data):
                self.readyPlugin = plugin
                return True
        return False
    def executeEvent(self, msg:str, data:Any)->Union[None, str]:
        if self.readyPlugin == None:
            warning("logic error in PluginGroupManager: executeEvent self.readyPlugin == None")
            return None
        if self.readyPlugin in ['enable', 'disable']:
            enabled = self.readyPlugin == 'enable'
            self.readyPlugin = None
            groupId = data["group_id"]
            if self.queryEnabled(groupId) != enabled:
                writeGlobalConfig(groupId, self.groupName + '.enable', enabled)
                self.enabledDict[groupId] = enabled
            send(data['group_id'], "OK")
            return "OK"
        else:
            try:
                result = self.readyPlugin.executeEvent(msg, data)
                self.readyPlugin = None
                return result
            except Exception as e:
                warning("logic error in PluginGroupManager: {}".format(e))
                return None
    def queryEnabled(self, groupId: int)->bool:
        if groupId not in self.enabledDict.keys():
            writeGlobalConfig(groupId, self.groupName, {'name':self.groupName, 'enable': self.defaultEnabled})
            self.enabledDict[groupId] = self.defaultEnabled
        return self.enabledDict[groupId]
```
