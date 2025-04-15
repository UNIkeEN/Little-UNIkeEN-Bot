from typing import Any, Union

from utils.basicEvent import *
from utils.standardPlugin import StandardPlugin


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
class FirecrackersFace(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg in ['点个鞭炮','鞭炮']
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        send(target, "[CQ:face,id=137,type=sticker]", data['message_type'])
        return "OK"
    def getPluginInfo(self, )->dict:
        return {
            'name': 'FirecrackersFace',
            'description': '鞭炮',
            'commandDescription': '点个鞭炮/鞭炮',
            'usePlace': ['group', 'private'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
class BasketballFace(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg in ['投个篮球','投篮']
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        send(target, "[CQ:face,id=114,type=sticker]", data['message_type'])
        return "OK"
    def getPluginInfo(self, )->dict:
        return {
            'name': 'BasketballFace',
            'description': '投篮',
            'commandDescription': '投个篮球/投篮',
            'usePlace': ['group', 'private'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
class HotFace(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg in ['热死了', '好热', '太热了']
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        send(target, "[CQ:face,id=340,type=sticker]", data['message_type'])
        return "OK"
    def getPluginInfo(self, )->dict:
        return {
            'name': 'HotFace',
            'description': '热化了',
            'commandDescription': '热死了/好热/太热了',
            'usePlace': ['group', 'private'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }