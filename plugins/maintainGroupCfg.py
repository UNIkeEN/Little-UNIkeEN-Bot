from typing import Union, Any
from utils.basicEvent import *
from utils.basicConfigs import *
from utils.functionConfigs import *
from utils.standardPlugin import StandardPlugin

class MtGroupCfg(StandardPlugin): 
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return startswith_in(msg,['-group cfg '])
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        if startswith_in(msg, ['-group cfg show']):
            send(data['group_id'], f'[CQ:image,file=files:///{ROOT_PATH}/'+show_config_card(data['group_id'])+',id=40000]')
            return "OK"
        if startswith_in(msg, ['-group cfg on ']):
            if not check_config(data['group_id'],'MaintainConfig',True,data['user_id']):
                send(data['group_id'],TXT_PERMISSION_DENIED_2)
            else:
                msg=msg.replace('-group cfg on ','',1)
                if edit_config(data['group_id'], msg ,True):
                    send(data['group_id'], f'权限修改成功[CQ:image,file=files:///{ROOT_PATH}/'+show_config_card(data['group_id'])+',id=40000]')
            return "OK"
        if startswith_in(msg, ['-group cfg off ']):
            if not check_config(data['group_id'],'MaintainConfig',True,data['user_id']):
                send(data['group_id'],TXT_PERMISSION_DENIED_2)
            else:
                msg=msg.replace('-group cfg off ','',1)
                if edit_config(data['group_id'], msg ,False):
                    send(data['group_id'], f'权限修改成功[CQ:image,file=files:///{ROOT_PATH}/'+show_config_card(data['group_id'])+',id=40000]')
            return "OK"
        if startswith_in(msg, ['-group cfg addadmin ']):
            if not check_config(data['group_id'],'MaintainConfig',True,data['user_id']):
                send(data['group_id'],TXT_PERMISSION_DENIED_2)
            else:
                msg=msg.replace('-group cfg addadmin ','',1)
                if add_admin(data['group_id'], msg):
                    send(data['group_id'], f'权限修改成功[CQ:image,file=files:///{ROOT_PATH}/'+show_config_card(data['group_id'])+',id=40000]')
            return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'MtGroupCfg',
            'description': '维护群聊权限',
            'commandDescription': '-grpcfg [...]',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }