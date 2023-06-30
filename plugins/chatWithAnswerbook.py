from typing import Union, Any
from utils.basicEvent import *
from utils.basicConfigs import *
from utils.standardPlugin import StandardPlugin
import json
import random
from time import sleep

book_path = 'resources/corpus/answerbook.json'
with open(book_path, "r", encoding='utf-8') as f:
    BOOK_DICT = json.load(f)

class ChatWithAnswerbook(StandardPlugin): # 答案之书
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return startswith_in(msg, ['小🦄，','小🦄,'])
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]: 
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        msg_inp = msg[2:]
        ran = random.sample(BOOK_DICT.keys(),1)[0]
        txt = BOOK_DICT[ran]["answer"]
        txt_cq = f'[CQ:reply,id='+str(data['message_id'])+']'+txt
        send(target, txt_cq, data['message_type'])
        # sleep(0.3)
        # voice = send_genshin_voice(txt+'。')
        # send(target, f'[CQ:record,file=files:///{ROOT_PATH}/{voice}]', data['message_type'])
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