from abc import ABC, abstractmethod
from typing import Union, Tuple, Any, List, final, Optional, Callable, Dict
from utils.basic_event import send, warning
from utils.config_api import read_global_config, write_global_config, get_group_admins
import re
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.job import Job
from threading import Timer


class NotPublishedException(BaseException):
    """可能有些插件因为secret key或者其他原因不选择开源，请抛出此类"""

    def __init__(self, what: str):
        self.what = what

    def __str__(self):
        return self.what


class StandardPlugin(ABC):
    """接收‘正常私聊消息或群消息’的接口"""

    @abstractmethod
    def judge_trigger(self, msg: str, data: Any) -> bool:
        """
        @msg: message text
        @data: all the message data, including group_id or user_id
        @return: whether trigger this class
        """
        raise NotImplementedError

    @abstractmethod
    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        """
        @msg: message text
        @data: all the message data, including group_id or user_id
        @return:
            if None, then continue tranversing following plugins
            if "OK", then stop tranversing
        """
        raise NotImplementedError

    @abstractmethod
    def get_plugin_info(self) -> dict:
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

    def on_state_change(self, nextState: bool, data: Any) -> None:
        """插件的状态（开启或关闭）改变时会调用此接口
        @nextState: 
            if True, plugin will open next
            if False, plugin will close next
        @data: all the message data, including group_id or user_id
        """


class EmptyPlugin(StandardPlugin):
    """空插件"""

    def __init__(self, *args, **kwargs) -> None:
        return

    def judge_trigger(self, msg: str, data: Any) -> bool:
        return False

    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        return None

    def get_plugin_info(self) -> dict:
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


class GuildStandardPlugin(StandardPlugin):
    """标准频道插件"""


class GuildEmptyPlugin(GuildStandardPlugin):
    """空QQ频道插件"""

    def __init__(self, *args, **kwargs) -> None:
        return

    def judge_trigger(self, msg: str, data: Any) -> bool:
        return False

    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        return None

    def get_plugin_info(self) -> dict:
        return {
            'name': 'GuildEmptyPlugin',
            'description': '空频道插件',
            'commandDescription': '',
            'usePlace': ['guild', ],
            'showInHelp': False,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }


class PokeStandardPlugin(ABC):
    """接收‘拍一拍’消息"""

    @abstractmethod
    def judge_trigger(self, data: Any) -> bool:
        """判断插件是否触发"""
        raise NotImplementedError

    @abstractmethod
    def poke_message(self, data: Any) -> Union[str, None]:
        """接收‘戳一戳’消息的接口
        @data: all the message data, from gocqhttp
        @return: 
            if None, 继续调用后续插件
            if "OK", 停止调用后续插件
        """
        raise NotImplementedError


class RecallMessageStandardPlugin(ABC):
    """接收‘撤回类型’消息"""

    @abstractmethod
    def recall_message(self, data: Any) -> Union[str, None]:
        """接收‘撤回类型’消息的接口
        @data: all the message data, from gocqhttp
        @return: 
            if None, 继续调用后续插件
            if "OK", 停止调用后续插件
        """
        raise NotImplementedError


class GroupUploadStandardPlugin(ABC):
    """接收‘上传文件’消息"""

    @abstractmethod
    def upload_file(self, data) -> Union[str, None]:
        """接收‘上传文件’消息的接口
        @data: all the message data, from gocqhttp
        @return: 
            if None, 继续调用后续插件
            if "OK", 停止调用后续插件
        """
        raise NotImplementedError


class AddGroupStandardPlugin(ABC):
    """接收‘加群申请’消息"""

    @abstractmethod
    def judge_trigger(self, data: Any) -> bool:
        """判断插件是否被触发：
            如果触发，则调用addGroupVerication方法
            否则继续往下遍历插件列表
        @data: all the message data, from gocqhttp
        @return: True or False, 代表是否触发
        """

    @abstractmethod
    def add_group_verication(self, data: Any) -> Union[str, None]:
        """接收‘加群申请’消息的接口
        @data: all the message data, from gocqhttp
        @return: 
            if None, 继续调用后续插件
            if "OK", 停止调用后续插件
        """


class EmptyAddGroupPlugin(AddGroupStandardPlugin):
    def __init__(self, *args, **kwargs) -> None:
        pass

    def judge_trigger(self, data) -> bool:
        return False

    def add_group_verication(self, data) -> Union[str, None]:
        return None


class BaseTimeSchedulePlugin(ABC):
    """定时任务基类，参考apscheduler文档"""
    scheduler = BackgroundScheduler()
    scheduler.start()

    @abstractmethod
    def tick(self, ) -> None:
        """每次触发任务所做的事情"""
        raise NotImplementedError

    @final
    def _tick(self, ) -> None:
        try:
            self.tick()
        except BaseException as e:
            warning('exception in ScheduleStandardPlugin: {}'.format(e))


class ScheduleStandardPlugin(BaseTimeSchedulePlugin):
    """固定每日时刻执行"""

    def schedule(self, hour: Union[str, int] = 0, minute: Union[str, int] = 0) -> Job:
        """可以重写此方法
        @hour: 
        @minute:
        e.g:
            hour: (str)'1-3', minute: None ---- 每天 1:00, 2:00, 3:00 运行
            hour: (int)0, minute: (int)1   ---- 每天 0:01 运行
        
        @return: this job
        """
        return BaseTimeSchedulePlugin.scheduler.add_job(self._tick, 'cron', hour=hour, minute=minute)


class CronStandardPlugin(BaseTimeSchedulePlugin):
    """间隔固定时长执行"""

    def start(self, startTime: float, intervalTime: float) -> Job:
        """开始执行，可以重写此方法
        @startTime: deprecated
        @intervalTime: 间隔多久执行一次任务，单位：秒

        @return: this job
        """
        return BaseTimeSchedulePlugin.scheduler.add_job(self._tick, 'interval', seconds=intervalTime)


class PluginGroupManager(StandardPlugin):
    refreshPluginStatusHandles: List[Tuple[str, Callable]] = []

    def __init__(self, plugins: List[StandardPlugin], groupName: str) -> None:
        self.plugins = plugins
        self.groupName = groupName
        self.readyPlugin = None
        self.enabledDict = read_global_config(None, groupName + '.enable')
        self.defaultEnabled = False
        self.groupInfo = {}
        self.onPattern = re.compile(r'^\-grpcfg\s+enable\s+(%s|\*)$' % self.groupName)
        self.offPattern = re.compile(r'^\-grpcfg\s+disable\s+(%s|\*)$' % self.groupName)
        self._check_group_info()
        PluginGroupManager.refreshPluginStatusHandles.append((groupName, self._refresh_plugin_status))

    @final
    def _check_group_info(self):
        # check group name
        if 'name' not in self.groupInfo.keys():
            self.groupInfo['name'] = self.groupName
        # check description
        if 'description' not in self.groupInfo.keys():
            description = '\n'.join([
                p.get_plugin_info()['description'] for p in self.plugins
            ])
            self.groupInfo['description'] = description
        # check command descrption
        if 'commandDescription' not in self.groupInfo.keys():
            commandDescription = '/'.join([
                p.get_plugin_info()['commandDescription'] for p in self.plugins
            ])
            self.groupInfo['commandDescription'] = commandDescription
        # check use place
        if not all(['group' in p.get_plugin_info()['usePlace'] for p in self.plugins]):
            warning('all plugins should be able to use in group, error in {}'.format(self.groupName))
        self.groupInfo['usePlace'] = ['group']

    def judge_trigger(self, msg: str, data: Any) -> bool:
        userId = data['user_id']
        groupId = data['group_id']
        if self.onPattern.match(msg) != None and userId in get_group_admins(groupId):
            self.readyPlugin = 'enable'
            return True
        if self.offPattern.match(msg) != None and userId in get_group_admins(groupId):
            self.readyPlugin = 'disable'
            return True
        if not self.query_enabled(groupId):
            return False
        for plugin in self.plugins:
            if plugin.judge_trigger(msg, data):
                self.readyPlugin = plugin
                return True
        return False

    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        if self.readyPlugin == None:
            warning("logic error in PluginGroupManager: executeEvent self.readyPlugin == None")
            return None
        if self.readyPlugin in ['enable', 'disable']:
            enabled = self.readyPlugin == 'enable'
            self.readyPlugin = None
            self.on_state_change(enabled, data)
            if msg[-1] == '*':
                return None
            else:
                send(data['group_id'], "[CQ:reply,id=%d]OK" % data['message_id'])
                return "OK"
        else:
            try:
                result = self.readyPlugin.execute_event(msg, data)
                self.readyPlugin = None
                return result
            except Exception as e:
                warning("logic error in PluginGroupManager [{}]: {}".format(self.groupName, e))
                return None

    def get_plugin_info(self, ) -> dict:
        return self.groupInfo

    def query_enabled(self, groupId: int) -> bool:
        if groupId not in self.enabledDict.keys():
            write_global_config(groupId, self.groupName, {'name': self.groupName, 'enable': self.defaultEnabled})
            self.enabledDict[groupId] = self.defaultEnabled
        return self.enabledDict[groupId]

    def set_enabled(self, groupId: int, enabled: bool):
        if self.query_enabled(groupId) != enabled:
            write_global_config(groupId, self.groupName + '.enable', enabled)
            self.enabledDict[groupId] = enabled

    def get_plugins(self) -> List[StandardPlugin]:
        return self.plugins

    def on_state_change(self, nextState: bool, data: Any) -> None:
        group_id = data['group_id']
        if nextState ^ self.query_enabled(group_id):
            self.set_enabled(group_id, nextState)
            for p in self.plugins:
                p.on_state_change(nextState, data)

    def _refresh_plugin_status(self):
        self.enabledDict = read_global_config(None, self.groupName + '.enable')

    @staticmethod
    def refresh_plugin_status(groupName: Union[str, None]):
        """刷新内存缓存
        if groupName == None:
            刷新所有注册在PluginGroupManager.refreshPluginStatusHandles
            的group缓存
        else:
            刷新注册在PluginGroupManager.refreshPluginStatusHandles
            且groupName与输入值相同的group的缓存
        """
        if groupName == None:
            for _, handle in PluginGroupManager.refreshPluginStatusHandles:
                handle()
        else:
            for grpn, handle in PluginGroupManager.refreshPluginStatusHandles:
                if grpn == groupName: handle()


class WatchDog(ABC):
    def __init__(self, intervalTime: float):
        """@intervalTime: how long (in seconds) will the dog hungry
        """
        self.intervalTime = intervalTime
        self.timer: Optional[Timer] = None

    def start(self):
        if self.timer == None:
            self.timer = Timer(self.intervalTime, self._on_hungry)
        self.timer.start()

    def resume(self):
        """resume if watchdog was paused or hungry previously"""
        if self.timer == None:
            self.timer = Timer(self.intervalTime, self._on_hungry)
            self.timer.start()

    def pause(self):
        """pause the watchdog"""
        if self.timer != None:
            self.timer.cancel()
            self.timer = None

    def feed(self):
        """feed the dog"""
        if self.timer != None:
            self.timer.cancel()
        self.timer = Timer(self.intervalTime, self._on_hungry)
        self.timer.start()

    def _on_hungry(self, ):
        try:
            self.on_hungry()
        except BaseException as e:
            warning('except in watch dog: {}'.format(e))
        finally:
            self.timer = None

    @abstractmethod
    def on_hungry(self):
        """If dog is hungry, what should you do? Do it here!"""
        raise NotImplementedError
