## 1. 插件简介

这个插件是特别针对作者的两个好朋友 —— 柴神和元神所开发的，以纪念他们对卖弱事业所作出的贡献。

| 插件名称 | 父类 | 触发关键词 | 触发权限 | 内容 |
| ---- | ---- | ---- | ---- | ---- |
| Chai_Jile | StandardPlugin | '寄了' / '我寄' | user_id = ${柴QQ} | patpat柴[CQ:face,id=49], 不要伤心😘 |
| Yuan_Jile | StandardPlugin | '真弱' / '寄了' / '好菜' | user_id = ${元QQ} | 😅😅😅😅😅😅😅😅😅😅 |

## 2. 代码分析

此代码位于 `jile.py`

```python
class Chai_Jile(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        柴的QQ号 = None
        return ('我寄' in msg or '寄了' in msg) and (data['user_id']==柴的QQ号)
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        send(data['group_id'], 'patpat柴[CQ:face,id=49], 不要伤心😘')
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'Chai_Jile',
            'description': '柴寄了',
            'commandDescription': '寄了',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
class Yuan_Jile(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        元的QQ号 = None
        应用QQ群 = None
        return ('真弱' in msg or '寄了' in msg or '好菜' in msg) and (data['user_id']==元的QQ号) and (data['group_id']==应用QQ群)
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        send(data['group_id'], '😅😅😅😅😅😅😅😅😅😅')
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'Yuan_Jile',
            'description': '元寄了',
            'commandDescription': '寄了',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }

```