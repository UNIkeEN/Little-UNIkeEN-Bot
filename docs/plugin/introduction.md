插件系统是基于class继承的一套系统，所有插件都必须继承`StandardPlugin`，并实现以下三个接口：

| 接口名称 | 参数 | 返回值类型 | 作用 |
| ---- | ---- | ---- | ---- |
| judgeTrigger | `@msg`: 消息文本，`str`类型<br>`@data`: 消息所包括的所有信息，`dict`类型 | `bool` | 判断此插件是否会触发 |
| executeEvent | `@msg`: 消息文本，`str`类型<br>`@data`: 消息所包括的所有信息，`dict`类型 | `str` 或者 `None` | 执行插件逻辑 |
| getPluginInfo |  `None` | `dict` | 返回插件信息 |

这里还要特别强调一下getPluginInfo的返回值格式：

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
| 'pluginConfigTableNames' | `list` | 这个插件所需要占用的数据库表名。注意，插件开发者开的sql表尽量挂在`BOT_DATA`这个库下面，因此需要避免表重名。 | 否 |
| 'version' | `str` | 插件版本 | 否 |
| 'author' | `str` | 插件作者 | 否 |

## 插件示范

```python
class FireworksFace(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg in ['放个烟花','烟花']
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        send(target, "[CQ:face,id=333,type=sticker]", data['message_type'])
        return "OK"
    def getPluginInfo(self, )->dict:
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
