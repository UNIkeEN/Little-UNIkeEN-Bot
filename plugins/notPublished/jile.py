from typing import Union, Any, List
from utils.basicEvent import send
from utils.standardPlugin import StandardPlugin, NotPublishedException

class Chai_Jile(StandardPlugin):
    def __init__(self, chai_qq:List[int] = []):
        super().__init__()
        self.chai_qq = chai_qq
        
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        if len(self.chai_qq) == 0: return False 
        return ('我寄' in msg or '寄了' in msg) and (data['user_id'] in self.chai_qq)
    
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        send(data['group_id'], 'patpat柴[CQ:face,id=49], 不要伤心😘')
        return "OK"
    
    def getPluginInfo(self, )->Any:
        return {
            'name': 'Chai_Jile',
            'description': '柴寄了',
            'commandDescription': '寄了',
            'usePlace': ['group', ],
            'showInHelp': len(self.chai_qq) > 0,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
        
class Yuan_Jile(StandardPlugin):
    def __init__(self, yuan_qq:List[int]=[]):
        super().__init__()
        self.yuan_qq = yuan_qq
        
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        if len(self.yuan_qq) == 0: return False
        return ('真弱' in msg or '寄了' in msg or '好菜' in msg) and (data['user_id'] in self.yuan_qq)
    
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        send(data['group_id'], '😅😅😅😅😅😅😅😅😅😅')
        return "OK"
    
    def getPluginInfo(self, )->Any:
        return {
            'name': 'Yuan_Jile',
            'description': '元寄了',
            'commandDescription': '寄了',
            'usePlace': ['group', ],
            'showInHelp': len(self.yuan_qq) > 0,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
        