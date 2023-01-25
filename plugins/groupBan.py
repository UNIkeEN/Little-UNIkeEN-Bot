from utils.standardPlugin import StandardPlugin
from typing import List, Any, Dict, Optional, Union
from utils.basicEvent import set_group_ban
class GroupBan(StandardPlugin):
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg in ['口球我']
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        set_group_ban(data['group_id'], data['user_id'], 60)
        return "OK"
    def getPluginInfo(self) -> dict:
        return {
            'name': 'GroupBan',
            'description': '被禁言一分钟',
            'commandDescription': '口球我',
            'usePlace': ['group', ],
            'showInHelp': False,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }