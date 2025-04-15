from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple, Union

from matplotlib import pyplot as plt

from utils.basicConfigs import ROOT_PATH, SAVE_TMP_PATH
from utils.basicEvent import get_group_member_list, send, warning
from utils.responseImage_beta import *
from utils.standardPlugin import StandardPlugin


def drawStatisticsPic(memberList:List[Dict[str, Any]], savePath:str)->Tuple[bool, str]:
    return True, savePath

class StatisticsReport(StandardPlugin):
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg == '-tj'
    def executeEvent(self, msg: str, data: Any) -> Optional[str]:
        groupId = data['group_id']
        send(groupId, '[CQ:reply,id=%d]正在生成群聊统计报告...'%(data['message_id']))
        memberList = get_group_member_list(groupId)
        savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'statistics-%d.png'%groupId)
        succ, reason = drawStatisticsPic(memberList, savePath)
        if succ:
            send(groupId, '[CQ:image,file=file:///%s]'%savePath)
        else:
            send(groupId, '[CQ:reply,id=%d]生成失败'%(data['message_id']))
        return 'OK'
    def getPluginInfo(self, )->Any:
        return {
            'name': 'ActReport',
            'description': '群聊统计报告',
            'commandDescription': '-tj',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
