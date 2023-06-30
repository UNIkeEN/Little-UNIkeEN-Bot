from typing import Union, Any
from utils.basicEvent import send
from utils.standardPlugin import StandardPlugin, NotPublishedException
try:
    from resources.api.secretQQ import CHAI_QQ, YUAN_QQ
except NotImplementedError:
    raise NotPublishedException("柴和元的QQ属于私密信息")

class Chai_Jile(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return ('我寄' in msg or '寄了' in msg) and (data['user_id']==CHAI_QQ)
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
        return ('真弱' in msg or '寄了' in msg or '好菜' in msg) and (data['user_id']==YUAN_QQ)
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