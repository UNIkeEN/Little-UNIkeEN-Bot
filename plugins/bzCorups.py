import random
from typing import Any, Union

from utils.basicEvent import send
from utils.standardPlugin import StandardPlugin


class BzGoldSentence(StandardPlugin):
    def __init__(self) -> None:
        try:
            with open('resources/corpus/bz.txt','r',encoding='utf-8') as f:
                bz_data = f.readlines()
        except:
            bz_data = None
        self.resource = bz_data
        
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg in ['ibz', '-bz', '-ibz'] and self.resource != None
    
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        sentence = random.choice(self.resource).strip()
        send(target, sentence, data['message_type'])
        return "OK"
    
    def getPluginInfo(self, )->Any:
        return {
            'name': 'BzGoldSentence',
            'description': 'bz金句',
            'commandDescription': '-bz / ibz',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Lonewiser',
        }