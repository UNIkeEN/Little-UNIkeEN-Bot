from typing import Union, Any
from utils.basic_event import send
from utils.standard_plugin import StandardPlugin
import random


class ZsmGoldSentence(StandardPlugin):
    def __init__(self) -> None:
        try:
            with open('resources/corpus/zsm.txt', 'r', encoding='utf-8') as f:
                zsm_data = f.readlines()
        except:
            zsm_data = None
        self.resource = zsm_data

    def judge_trigger(self, msg: str, data: Any) -> bool:
        return msg in ['zsm', 'ism', '-zsm', '-ism'] and self.resource != None

    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type'] == 'group' else data['user_id']
        sentence = random.choice(self.resource).strip()
        send(target, sentence, data['message_type'])
        return "OK"

    def get_plugin_info(self, ) -> Any:
        return {
            'name': 'ZsmGoldSentence',
            'description': 'zsm金句',
            'commandDescription': 'zsm / ism',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.2',
            'author': 'Unicorn',
        }
