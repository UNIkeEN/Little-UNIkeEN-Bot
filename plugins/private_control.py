from utils.basic_event import send, warning, startswith_in
from utils.config_api import read_global_config, write_global_config
from utils.standard_plugin import StandardPlugin, PluginGroupManager
from utils.basic_configs import ROOT_ADMIN_ID, APPLY_GROUP_ID
from utils.configs_loader import add_group_to_apply_id, del_group_from_apply_id, get_apply_groups
from typing import Any, List, Union
import re
from .help_v2 import draw_help_card


class LsGroup(StandardPlugin):
    def judge_trigger(self, msg: str, data: Any) -> bool:
        return msg in ['-lsgroup', '-lsgrp'] and data['user_id'] in ROOT_ADMIN_ID

    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type'] == 'group' else data['user_id']
        result = []
        for idx, (groupId, description) in enumerate(get_apply_groups()):
            result.append(str(idx + 1) + '. ' + str(groupId) + ': ' + description)
        send(target, '\n'.join(result), data['message_type'])
        return 'OK'

    def get_plugin_info(self, ) -> Any:
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
        self.plugins = None

    def judge_trigger(self, msg: str, data: Any) -> bool:
        return self.triggerPattern.match(msg) != None and data['user_id'] in ROOT_ADMIN_ID

    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type'] == 'group' else data['user_id']
        grpId = int(self.triggerPattern.findall(msg)[0])
        if grpId not in APPLY_GROUP_ID:
            send(target, '[CQ:reply,id=%d]该群尚未加入白名单' % data['message_id'], data['message_type'])
        elif self.plugins == None:
            send(target, '[CQ:reply,id=%d]BUG: self.plugins==None, 请上报管理员' % data['message_id'],
                 data['message_type'])
        else:
            imgPath = draw_help_card(self.plugins, grpId)
            send(target, '[CQ:image,file=files:///%s]' % imgPath, data['message_type'])
        return "OK"

    def get_plugin_info(self, ) -> Any:
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

    def setPluginList(self, plugins: List[StandardPlugin]):
        self.plugins = plugins


class GroupApply(StandardPlugin):
    def __init__(self):
        self.onPattern = re.compile(r'^-enable\s+(\d+)\s+(.*)')
        self.offPattern = re.compile(r'-disable\s+(\d+)')

    def judge_trigger(self, msg: str, data: Any) -> bool:
        return startswith_in(msg, ['-enable', '-disable']) and data['user_id'] in ROOT_ADMIN_ID

    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type'] == 'group' else data['user_id']
        if self.onPattern.match(msg) != None:
            groupId, description = self.onPattern.findall(msg)[0]
            groupId = int(groupId)
            if len(description) > 100:
                send(target, '[CQ:reply,id=%d]添加失败，群描述长度超限' % data['message_id'], data['message_type'])
            else:
                add_group_to_apply_id(groupId, description)
                send(target, '[CQ:reply,id=%d]OK' % data['message_id'], data['message_type'])
        elif self.offPattern.match(msg) != None:
            groupId = self.offPattern.findall(msg)[0]
            groupId = int(groupId)
            if groupId in APPLY_GROUP_ID:
                del_group_from_apply_id(groupId)
                send(target, '[CQ:reply,id=%d]OK' % data['message_id'], data['message_type'])
            else:
                send(target, '[CQ:reply,id=%d]该群不在白名单中' % data['message_id'], data['message_type'])
        else:
            send(target, '[CQ:reply,id=%d]指令识别失败，请输入-help获取帮助' % data['message_id'], data['message_type'])
        return 'OK'

    def get_plugin_info(self, ) -> Any:
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

    def judge_trigger(self, msg: str, data: Any) -> bool:
        return self.triggerPattern.match(msg) != None and data['user_id'] in ROOT_ADMIN_ID

    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type'] == 'group' else data['user_id']
        mode, groupId, pluginName = self.triggerPattern.findall(msg)[0]
        enabled = mode == 'on'
        groupId = int(groupId)
        prevConf = read_global_config(groupId, pluginName)
        if prevConf == None:
            send(target, f'[CQ:reply,id={data["message_id"]}]不存在群 {groupId} 或此群【{pluginName}】插件尚未初始化',
                 data['message_type'])
        elif prevConf['enable'] == enabled:
            send(target,
                 f'[CQ:reply,id={data["message_id"]}]群 {groupId} 插件【{pluginName}】已{"开启" if enabled else "关闭"}',
                 data['message_type'])
        else:
            write_global_config(groupId, pluginName + '.enable', enabled)
            PluginGroupManager.refresh_plugin_status(pluginName)
            send(target, f'[CQ:reply,id={data["message_id"]}]OK', data['message_type'])
        return "OK"

    def get_plugin_info(self, ) -> Any:
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
