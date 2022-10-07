Little-UNIkeEN-Bot 通过插件机制实现功能的开发，通过维护插件列表实现功能的增减。

## 插件逻辑

所有插件都必须继承于 `StandardPlugin` 类，并实现以下三个接口函数：

| 接口名称 | 参数 | 返回值类型 | 作用 |
| ---- | ---- | ---- | ---- |
| judgeTrigger | `@msg`: 消息文本，`str`类型<br>`@data`: 消息所包括的所有信息，`dict`类型 | `bool` | 判断此插件是否会触发 |
| executeEvent | `@msg`: 消息文本，`str`类型<br>`@data`: 消息所包括的所有信息，`dict`类型 | `str` 或者 `None` | 执行插件逻辑 |
| getPluginInfo |  `None` | `dict` | 返回插件信息 |

开发者在 `main.py` 中 `import` 功能插件，并维护 `main.py` 中的插件列表以增减插件，关于插件的具体示例请见下一节。

Bot 运行收到群聊/私聊消息时，将遍历群聊/私聊插件列表，逐一调用各插件的 `judgeTrigger()` 函数，若返回值为真则触发，调用该插件的 `executeEvent()` 函数进行响应。插件的 `getPluginInfo()` 函数则在用户获取帮助信息时被逐一调用。

特别强调，关于 `getPluginInfo()` 的返回值格式，要求如下：

```python
{
    'name': 'Faq',                      # require
    'description': '问答库',             # require
    'commandDescription': '问 [title]', # require
    'usePlace': ['group', 'private', ], # require
    'showInHelp': True,                 # suggest, default True
    'pluginConfigTableNames': ['Faq',], # suggest, must be unique among plugins
    'version': '1.0.0',                 # suggest
    'author': 'Unicorn',                # suggest
    ...                                 # any other information you want
}
```

| 名称 | 类型 | 作用 | 是否必须 |
| ---- | ---- | ---- | ---- |
| 'name' | `str` | 提示这个插件的class名称 | 是 |
| 'description' | `str` | 简要描述这个插件 | 是 |
| 'commandDescription' | `str` | 概括触发这个插件的关键词 | 是 |
| 'usePlace' | `list` | 描述这个插件的作用域<br>'private': 这个插件可以在私聊开启<br>'group': 这个插件可以在群聊开启 | 是 |
| 'showInHelp' | `bool` | 是否在help时展示 | 否，默认`True` |
| 'pluginConfigTableNames' | `list` | 这个插件所需要占用的数据库表名。注意，插件开发者创建的sql表尽量挂在`BOT_DATA`这个库下面，因此需要避免表重名。 | 否 |
| 'version' | `str` | 插件版本 | 否 |
| 'author' | `str` | 插件作者 | 否 |

## 插件示范

以下的代码可以实现，在群聊或私聊中有人发送关键词“放个烟花”或“烟花”时，Bot 回复超级表情“烟花”。

`plugins/superEmoji.py` 中实现插件功能代码：

```python hl_lines="3 10"
from typing import Union, Any
from utils.basicEvent import *
from utils.standardPlugin import StandardPlugin # 引入StandardPlugin

class FireworksFace(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg in ['放个烟花','烟花']
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        send(target, "[CQ:face,id=333,type=sticker]", data['message_type']) # 发送消息
        return "OK"
    def getPluginInfo(self, ) -> dict:
        return {
            'name': 'FireworksFace',
            'description': '烟花',
            'commandDescription': '放个烟花/烟花',
            'usePlace': ['group', 'private'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
```

发送消息函数 `send()` 的具体参数与功能请见 API。

在 `main.py` 的插件列表中启用插件：

```python hl_lines="4 7"
from plugins.superEmoji import *
...
GroupPluginList=[ # 群插件列表
    ..., FireworksFace(), # 在此处添加插件类以在群聊时启用
]
PrivatePluginList=[ # 私聊启用插件
    ..., FireworksFace(), # 在此处添加插件类以在私聊时启用
]
```

!!! tip "提示：代码结构"
    为便于管理，我们推荐将功能插件的代码文件放在 `plugins/` 目录下，并在 `main.py` 中 `import` 。如果有需要，你可以随意更改此代码结构。
!!! warning "注意：触发条件冲突"
    Bot 在设计时默认一句指令只能进行一次响应，开发者请尽量确保触发条件不冲突，或考虑插件列表中各插件的先后顺序。
    如某一插件触发但不提供响应，可以返回 None 以继续执行列表中的后续插件。

## 代码分析

```python
# parts of utils/standardPlugin.py
from abc import ABC, abstractmethod
from typing import Union, Tuple, Any, List

class StandardPlugin(ABC):
    @abstractmethod
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        """
        @msg: message text
        @data: all the message data, including group_id or user_id
        @return: whether trigger this class
        """
        raise NotImplementedError
    
    @abstractmethod
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        """
        @msg: message text
        @data: all the message data, including group_id or user_id
        @return:
            if None, then continue tranversing following plugins
            if "OK", then stop tranversing
        """
        raise NotImplementedError

    @abstractmethod
    def getPluginInfo(self)->dict:
        """
        @return:
            a dict object like:
            {
                'name': 'Faq',                      # require
                'description': '问答库',             # require
                'commandDescription': '问 [title]', # require
                'usePlace': ['group', 'private', ], # require
                'showInHelp': True,                 # suggest, default True
                'pluginConfigTableNames': ['Faq',], # suggest, must be unique among plugins
                'version': '1.0.0',                 # suggest
                'author': 'Unicorn',                # suggest
                ...                                 # any other information you want
            }
        """
        raise NotImplementedError
```
