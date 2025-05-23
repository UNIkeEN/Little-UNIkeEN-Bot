import json
import random
from typing import Any, Dict, List, Union

from utils.basicConfigs import *
from utils.basicEvent import *
from utils.standardPlugin import StandardPlugin

book_path = 'resources/corpus/answerbook.json'
with open(book_path, "r", encoding='utf-8') as f:
    result:Dict[str, Dict[str, str]] = json.load(f)
    BOOK_DICT = [x['answer'] for x in result.values()]

class ChatWithAnswerbook(StandardPlugin): # 答案之书
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return startswith_in(msg, ['小🦄', '小马'])
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]: 
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        txt = random.choice(BOOK_DICT)
        txt_cq = f'[CQ:reply,id='+str(data['message_id'])+']'+txt
        send(target, txt_cq, data['message_type'])
        return "OK"
    
    def getPluginInfo(self, )->Any:
        return {
            'name': 'ChatWithAnswerbook',
            'description': '答案之书',
            'commandDescription': '小🦄，[...]',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }