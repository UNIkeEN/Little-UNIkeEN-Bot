from typing import Any, Union
from utils.sqlUtils import newSqlSession
from utils.basicConfigs import ROOT_ADMIN_ID
from utils.basicEvent import send
from utils.standardPlugin import StandardPlugin
import re
from typing import Optional
class Eavesdrop(StandardPlugin):
    def __init__(self) -> None:
        self.pattern = re.compile(r'^\^\s*(\d*)$')
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return self.pattern.match(msg) != None and data['user_id'] in ROOT_ADMIN_ID
    def executeEvent(self, msg: str, data: Any) -> Optional[str]:
        groupId = data['group_id']
        num = self.pattern.findall(msg)[0]
        if len(num) == 0:
            num = 0
        else:
            num = int(num)
        mydb, mycursor = newSqlSession()
        if num < 0 or num > 20:
            send(groupId, '数字有误，请输入合适的数字落入区间[0,20]')
            return 'OK'
        mycursor.execute("""select `user_id`, `time`, if(card = '', nickname, card), `message` from messageRecord where
                         group_id = %d and recall = true order by message_seq desc limit %d, 1"""%(
                             groupId, num
                         ))
        result = list(mycursor)
        if len(result) == 0:
            send(groupId, '好像没有偷听到内容呢~')
        else:
            userId, sendTime, nick, message = result[0]
            send(groupId, '偷听用户 %s(%d) 于 %s 发送后撤回的信息：\n%s'%(
                nick, userId, sendTime.strftime('%Y-%m-%d %H:%M:%S'), message
            ))
        return 'OK'
    def getPluginInfo(self) -> dict:
        return {
            'name': 'Eavesdrop',
            'description': '偷听撤回消息',
            'commandDescription': '^(\d+)?',
            'usePlace': ['group', ],
            'showInHelp': False,                
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }