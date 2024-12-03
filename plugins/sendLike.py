from utils.standardPlugin import StandardPlugin
from typing import List, Any, Dict, Optional, Union, Set, Tuple
from utils.basicEvent import set_group_ban, isGroupOwner, send, warning, send_like
from utils.configAPI import getGroupAdmins
from utils.basicConfigs import ROOT_ADMIN_ID, SAVE_TMP_PATH, ROOT_PATH, BOT_SELF_QQ
from utils.sqlUtils import newSqlSession

class SendLike(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return (msg in ['赞下'])
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        send_like(data['user_id'], 10)
        send(target, '[CQ:reply,id=%d]已赞（如果没出啥问题的话）'%data['message_id'], data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'SendLike',
            'description': '点赞',
            'commandDescription': '赞下',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }