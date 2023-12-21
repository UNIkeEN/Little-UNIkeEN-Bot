from utils.basicEvent import send, warning, startswith_in
from utils.configAPI import readGlobalConfig, writeGlobalConfig
from utils.standardPlugin import StandardPlugin, PluginGroupManager
from utils.basicConfigs import ROOT_ADMIN_ID, APPLY_GROUP_ID
from utils.configsLoader import addGroupToApplyId, delGroupFromApplyId, getApplyGroups
from typing import Any, List, Union
import re
from .help_v2 import drawHelpCard

class LsGroup(StandardPlugin):
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg in ['-lsgroup', '-lsgrp'] and data['user_id'] in ROOT_ADMIN_ID
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        result = []
        for idx, (groupId, description) in enumerate(getApplyGroups()):
            result.append(str(idx+1)+'. '+str(groupId) + ': ' + description)
        if len(result) > 0:
            send(target, '\n'.join(result), data['message_type'])
        else:
            send(target, '机器人暂未在任何群聊开启', data['message_type'])
        return 'OK'
    def getPluginInfo(self, )->Any:
        return {
            'name': 'LsGroup',
            'description': '查询开启群[🔒]',
            'commandDescription': '-lsgroup/-lsgrp',
            'usePlace': ['group', 'private'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }

class HelpInGroup(StandardPlugin):
    def __init__(self):
        self.triggerPattern = re.compile(r'^-grpcfg\s+(\d+)')
        self.plugins= None
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return self.triggerPattern.match(msg) != None and data['user_id'] in ROOT_ADMIN_ID
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        grpId = int(self.triggerPattern.findall(msg)[0])
        if grpId not in APPLY_GROUP_ID:
            send(target, '[CQ:reply,id=%d]该群尚未加入白名单'%data['message_id'], data['message_type'])
        elif self.plugins == None:
            send(target, '[CQ:reply,id=%d]BUG: self.plugins==None, 请上报管理员'%data['message_id'], data['message_type'])
        else:
            imgPath = drawHelpCard(self.plugins, grpId)
            send(target, '[CQ:image,file=file:///%s]'%imgPath, data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'HelpInGroup',
            'description': '绘制群聊帮助[🔒]',
            'commandDescription': '-grpcfg [群号]',
            'usePlace': ['group', 'private'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
    def setPluginList(self, plugins:List[StandardPlugin]):
        self.plugins = plugins
class GroupApply(StandardPlugin):
    def __init__(self):
        self.onPattern = re.compile(r'^-enable\s+(\d+)\s+(.*)')
        self.offPattern = re.compile(r'-disable\s+(\d+)')
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return startswith_in(msg, ['-enable', '-disable']) and data['user_id'] in ROOT_ADMIN_ID
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        if self.onPattern.match(msg) != None:
            groupId, description = self.onPattern.findall(msg)[0]
            groupId = int(groupId)
            if len(description) > 100:
                send(target, '[CQ:reply,id=%d]添加失败，群描述长度超限'%data['message_id'], data['message_type'])
            else:
                addGroupToApplyId(groupId, description)
                send(target, '[CQ:reply,id=%d]OK'%data['message_id'], data['message_type'])
        elif self.offPattern.match(msg) != None:
            groupId = self.offPattern.findall(msg)[0]
            groupId = int(groupId)
            if groupId in APPLY_GROUP_ID:
                delGroupFromApplyId(groupId)
                send(target, '[CQ:reply,id=%d]OK'%data['message_id'], data['message_type'])
            else:
                send(target, '[CQ:reply,id=%d]该群不在白名单中'%data['message_id'], data['message_type'])
        else:
            send(target, '[CQ:reply,id=%d]指令识别失败，请输入-help获取帮助'%data['message_id'], data['message_type'])
        return 'OK'
    def getPluginInfo(self, )->Any:
        return {
            'name': 'GroupApply',
            'description': '开关群[🔒]',
            'commandDescription': '-enable [群号] [群简介] / -disable [群号]',
            'usePlace': ['group', 'private'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
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
        if groupId not in APPLY_GROUP_ID:
            send(target, f'[CQ:reply,id={data["message_id"]}]机器人尚未在群 {groupId} 开启', data['message_type'])
        elif prevConf == None:
            writeGlobalConfig(groupId, pluginName+'.enable', enabled)
            PluginGroupManager.refreshPluginStatus(pluginName)
            send(target, f'[CQ:reply,id={data["message_id"]}]OK', data['message_type'])
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
            'description': '开关群插件[🔒]',
            'commandDescription': '-(on|off) [群号] [插件名]',
            'usePlace': ['group', 'private'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }