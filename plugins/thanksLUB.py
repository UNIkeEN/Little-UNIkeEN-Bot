from typing import Any, Union, List, Tuple, Optional
from utils.standardPlugin import StandardPlugin
from utils.basicEvent import send, warning, startswith_in
from utils.basicConfigs import ROOT_PATH, SAVE_TMP_PATH
import random
class ThanksLUB(StandardPlugin):
    def __init__(self) -> None:
        self.replyList = [
            '这是我应该做的',
            '不用谢，请多多指教',
            '谢谢你喜欢我',
            '这是我的荣幸',
            '我喜欢为大家服务',
            '谢谢',
            '爱你哟',
            '记得请我吃饭',
            '爱我，就用RMB狠狠砸我',
            '不客气，举手之劳',
            '我是专为大家服务的机器人',
            '请ynk喝杯快乐水吧',
            '请方珠子喝杯快乐水吧',
            'https://github.com/UNIkeEN/Little-UNIkeEN-Bot 给个star谢谢喵',
            'https://github.com/UNIkeEN/Little-UNIkeEN-Bot 给个star谢谢喵',
        ]
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return startswith_in(msg, ['谢谢小马', '谢谢小🦄'])
    def executeEvent(self, msg: str, data: Any) -> Optional[str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        send(target, '[CQ:reply,id=%d]%s'%(data['message_id'], random.choice(self.replyList)), data['message_type'])
        return 'OK'
    def getPluginInfo(self, )->Any:
        return {
            'name': 'ThanksLUB',
            'description': '谢谢小马',
            'commandDescription': '谢谢小马',
            'usePlace': ['group', 'private', ],
            'showInHelp': False,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }