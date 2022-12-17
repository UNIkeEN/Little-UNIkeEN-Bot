from abc import ABC, abstractmethod
from typing import Union, Tuple, Any, List
from utils.basicEvent import send, warning, readGlobalConfig, writeGlobalConfig, getGroupAdmins
from threading import Timer, Semaphore
import re

class StandardPlugin(ABC):
    """接收‘正常私聊消息或群消息’的接口"""
    @abstractmethod
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        """
        @msg: message text
        @data: all the message data, including group_id or user_id
        @return: whether trigger this class
        """
        raise NotImplementedError
    
    @abstractmethod
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        """
        @msg: message text
        @data: all the message data, including group_id or user_id
        @return:
            if None, then continue tranversing following plugins
            if "OK", then stop tranversing
        """
        raise NotImplementedError

    @abstractmethod
    def getPluginInfo(self)->dict:
        """
        @return:
            a dict object like:
            {
                'name': 'Faq',                      # require
                'description': '问答库',             # require
                'commandDescription': '问 [title]', # require
                'usePlace': ['group', 'private', ], # require
                'showInHelp': True,                 # suggest, default True
                'pluginConfigTableNames': ['Faq',], # suggest, must be unique among plugins
                'version': '1.0.0',                 # suggest
                'author': 'Unicorn',                # suggest
                ...                                 # any other information you want
            }
        """
        raise NotImplementedError

class EmptyPlugin(StandardPlugin):
    """空插件"""
    def __init__(self, *args, **kwargs) -> None:
        return
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return False
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        return None
    def getPluginInfo(self) -> dict:
        return {
            'name': 'EmptyPlugin',
            'description': '空插件',
            'commandDescription': '',
            'usePlace': ['group', 'private', ],
            'showInHelp': False,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }

class RecallMessageStandardPlugin(ABC):
    """接收‘撤回类型’消息的接口"""
    @abstractmethod
    def recallMessage(self, data:Any)->Union[str, None]:
        raise NotImplementedError

class GroupUploadStandardPlugin(ABC):
    """接收‘上传文件’消息的接口"""
    @abstractmethod
    def uploadFile(self, data)->Union[str, None]:
        raise NotImplementedError
class CronStandardPlugin(ABC):
    def __init__(self) -> None:
        self.timer = None
        self.intervalTime = 180
    @abstractmethod
    def tick(self,)->None:
        raise NotImplementedError
    def _tick(self)->None:
        self.timer.cancel()
        self.timer = Timer(self.intervalTime, self._tick)
        self.timer.start()
        try:
            self.tick()
        except BaseException as e:
            warning('base exception in CronStandardPlugin: {}'.format(e))
    def start(self, startTime:float, intervalTime:float)->None:
        self.timer = Timer(startTime, self._tick)
        self.intervalTime = intervalTime
        self.timer.start()

class PluginGroupManager(StandardPlugin):
    def __init__(self, plugins:List[StandardPlugin], groupName: str) -> None:
        self.plugins = plugins
        self.groupName = groupName
        self.readyPlugin = None
        self.enabledDict = readGlobalConfig(None, groupName+'.enable')
        self.defaultEnabled = False
        self.groupInfo = {}
        self.onPattern = re.compile(r'^\-grpcfg\s+enable\s+(%s|\*)$'%self.groupName)
        self.offPattern = re.compile(r'^\-grpcfg\s+disable\s+(%s|\*)$'%self.groupName)
        self._checkGroupInfo()

    def _checkGroupInfo(self):
        # check group name
        if 'name' not in self.groupInfo.keys():
            self.groupInfo['name'] = self.groupName
        # check description
        if 'description' not in self.groupInfo.keys():
            description = '\n'.join([
                p.getPluginInfo()['description'] for p in self.plugins
            ])
            self.groupInfo['description'] = description
        # check command descrption
        if 'commandDescription' not in self.groupInfo.keys():
            commandDescription = '/'.join([
                p.getPluginInfo()['commandDescription'] for p in self.plugins
            ])
            self.groupInfo['commandDescription'] = commandDescription
        # check use place
        if not all(['group' in p.getPluginInfo()['usePlace'] for p in self.plugins]):
            warning('all plugins should be able to use in group, error in {}'.format(self.groupName))
        self.groupInfo['usePlace'] = ['group']

    def judgeTrigger(self, msg:str, data:Any)->bool:
        userId = data['user_id']
        groupId = data['group_id']
        if self.onPattern.match(msg) != None and userId in getGroupAdmins(groupId):
            self.readyPlugin = 'enable'
            return True
        if self.offPattern.match(msg) != None and userId in getGroupAdmins(groupId):
            self.readyPlugin = 'disable'
            return True
        if not self.queryEnabled(groupId):
            return False
        for plugin in self.plugins:
            if plugin.judgeTrigger(msg, data):
                self.readyPlugin = plugin
                return True
        return False
    def executeEvent(self, msg:str, data:Any)->Union[None, str]:
        if self.readyPlugin == None:
            warning("logic error in PluginGroupManager: executeEvent self.readyPlugin == None")
            return None
        if self.readyPlugin in ['enable', 'disable']:
            enabled = self.readyPlugin == 'enable'
            self.readyPlugin = None
            groupId = data["group_id"]
            if msg[-1] == '*':
                self.recursiveSetEnabled(groupId, enabled)
                return None
            if enabled:
                self.setEnabled(groupId, enabled)
            else:
                self.recursiveSetEnabled(groupId, enabled)
            send(data['group_id'], "[CQ:reply,id=%d]OK"%data['message_id'])
            return "OK"
        else:
            try:
                result = self.readyPlugin.executeEvent(msg, data)
                self.readyPlugin = None
                return result
            except Exception as e:
                warning("logic error in PluginGroupManager [{}]: {}".format(self.groupName, e))
                return None
    def getPluginInfo(self, )->dict:
        return self.groupInfo
    def queryEnabled(self, groupId: int)->bool:
        if groupId not in self.enabledDict.keys():
            writeGlobalConfig(groupId, self.groupName, {'name':self.groupName, 'enable': self.defaultEnabled})
            self.enabledDict[groupId] = self.defaultEnabled
        return self.enabledDict[groupId]
    def setEnabled(self, groupId: int, enabled: bool):
        if self.queryEnabled(groupId) != enabled:
            writeGlobalConfig(groupId, self.groupName + '.enable', enabled)
            self.enabledDict[groupId] = enabled
    def recursiveSetEnabled(self, groupId: int, enabled: bool):
        self.setEnabled(groupId, enabled)
        for p in self.getPlugins():
            if issubclass(type(p), PluginGroupManager):
                p: PluginGroupManager
                p.recursiveSetEnabled(groupId, enabled)
    def getPlugins(self)->List[StandardPlugin]:
        return self.plugins