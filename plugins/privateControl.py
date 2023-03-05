from utils.basicEvent import send, warning, readGlobalConfig, writeGlobalConfig
from utils.standardPlugin import StandardPlugin, PluginGroupManager
from utils.basicConfigs import ROOT_ADMIN_ID
from typing import Any, List, Union
import re

class PrivateControl(StandardPlugin):
    def __init__(self) -> None:
        self.triggerPattern = re.compile(r'^\-(on|off)\s+(\d+)\s+([a-zA-Z0-9]+)')
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return self.triggerPattern.match(msg) != None and data['user_id'] in ROOT_ADMIN_ID
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        mode, groupId, pluginName = self.triggerPattern.findall(msg)[0]
        enabled = mode == 'on'
        groupId = int(groupId)
        prevConf = readGlobalConfig(groupId, pluginName)
        if prevConf == None:
            send(target, f'[CQ:reply,id={data["message_id"]}]不存在群 {groupId} 或此群【{pluginName}】插件尚未初始化', data['message_type'])
        elif prevConf['enable'] == enabled:
            send(target, f'[CQ:reply,id={data["message_id"]}]群 {groupId} 插件【{pluginName}】已{"开启" if enabled else "关闭"}', data['message_type'])
        else:
            writeGlobalConfig(groupId, pluginName+'.enable', enabled)
            PluginGroupManager.refreshPluginStatus(pluginName)
            send(target, f'[CQ:reply,id={data["message_id"]}]OK', data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'PrivateControl',
            'description': '管理员开启群插件',
            'commandDescription': '-(on|off) [群号] [插件名]',
            'usePlace': ['group', 'private'],
            'showInHelp': False,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }