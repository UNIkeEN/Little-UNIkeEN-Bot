from typing import Union, Any
import psutil
from utils.basicEvent import *
from utils.basicConfigs import *
from utils.standardPlugin import StandardPlugin, PluginGroupManager
from utils.responseImage import *
import os.path
import re
class ShowHelp(StandardPlugin): 
    def __init__(self) -> None:
        self.pattern = re.compile(r'^\-help\s*(.*)$')
        self.subdevidePattern = re.compile(r'^(\S+)\s+(\S.*)$')
        self.pluginList = []
        self.pluginListPrivate = []
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return self.pattern.match(msg) != None
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        group_id = data['group_id'] if data['message_type']=='group' else 0
        helpWords = self.pattern.findall(msg)[0]
        def getTargetPluginList(pluginList:List[StandardPlugin], helpWords:str)->List[StandardPlugin]:
            if helpWords == '':
                return pluginList
            if self.subdevidePattern.match(helpWords) != None:
                currentPlugin, nextHelpWords = self.subdevidePattern.findall(helpWords)[0]
                for p in pluginList:
                    if not isinstance(p, PluginGroupManager): continue
                    p: PluginGroupManager
                    if p.groupName == currentPlugin:
                        return getTargetPluginList(p.plugins, nextHelpWords)
                return []
            else:
                for p in pluginList:
                    if not isinstance(p, PluginGroupManager): continue
                    p: PluginGroupManager
                    if p.groupName == helpWords:
                        return p.plugins
                return []
        targetPluginList = self.pluginList if data['message_type']=='group' else self.pluginListPrivate
        targetPluginList = getTargetPluginList(targetPluginList, helpWords)
        if len(targetPluginList) == 0:
            send(target, '[CQ:reply,id=%d]暂未创建对应名称的模块'%data['message_id'], data['message_type'])
        else:
            imgPath = drawHelpCard(targetPluginList, group_id)
            imgPath = imgPath if os.path.isabs(imgPath) else os.path.join(ROOT_PATH, imgPath)
            send(target, '[CQ:image,file=files:///%s]'%imgPath, data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'ShowHelp',
            'description': '帮助',
            'commandDescription': '-help [...]?'
                '\n群主权限标识: 👑'
                '\nROOT权限标识: 🔒'
                '\n群BOT管理权限标识: 🔑'
                '\n开启插件组[🔑]:  -grpcfg enable <组名>'
                '\n关闭插件组[🔑]:  -grpcfg disable <组名>'
                '\n插件组可嵌套，开启内层插件组须先打开外层'
                ,
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.4',
            'author': 'Unicorn',
        }
    def updatePluginList(self, plugins, private_plugins):
        for plugin in plugins:
            if issubclass(type(plugin), StandardPlugin):
                self.pluginList.append(plugin)
            else:
                warning("unexpected plugin {} type in ShowHelp plugin".format(plugin))
        for plugin in private_plugins:
            if issubclass(type(plugin), StandardPlugin):
                self.pluginListPrivate.append(plugin)
            else:
                warning("unexpected plugin {} type in ShowHelp plugin".format(plugin))

def drawHelpCard(pluginList, group_id)->str:
    helpCards = ResponseImage(
        title = '群聊功能配置' if group_id!=0 else '私聊功能配置', 
        footer = (f'当前群号:{group_id}' if group_id!=0 else ''),
        titleColor = PALETTE_CYAN,
        layout = 'two-column',
        width = 1280,
        cardBodyFont= ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 24),
        cardSubtitleFont= ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 24),
    )
    for item in pluginList:
        cardPluginList = []
        flag = False
        if isinstance(item, PluginGroupManager):
            item: PluginGroupManager
            flag = item.queryEnabled(group_id)
            cardPluginList.append(('title', item.groupName))
            cardPluginList.append(('separator', ))
            for plugin in item.plugins:
                infoDict:dict = plugin.getPluginInfo()
                if 'showInHelp' in infoDict.keys() and not infoDict['showInHelp']:
                    continue
                try:
                    if isinstance(plugin, PluginGroupManager):
                        plugin: PluginGroupManager
                        cardPluginList.append((
                            'body' if plugin.queryEnabled(group_id) else 'subtitle',
                            "[插件组] "+ plugin.groupName + '\n' +
                                infoDict['description']
                        ))
                    else:
                        cardPluginList.append(('body',(infoDict['description']+':  '+infoDict['commandDescription'])))
                except KeyError:
                    warning('meet KeyError when getting help, plugin: {}'.format(plugin))
        else:
            item: StandardPlugin
            flag = True
            infoDict = item.getPluginInfo()
            if 'showInHelp' in infoDict.keys() and not infoDict['showInHelp']:
                continue
            try:
                cardPluginList.append(('body',(infoDict['description']+':  '+infoDict['commandDescription'])))
            except KeyError:
                warning('meet KeyError when getting help, plugin: {}'.format(item))
        
        if len(cardPluginList)>0:
            clr = PALETTE_GREY if not flag else PALETTE_CYAN
            clr2 = PALETTE_GREY if not flag else PALETTE_BLACK
            helpCards.addCard(ResponseImage.RichContentCard(raw_content=cardPluginList, titleFontColor=clr ,bodyFontColor=clr2,subtitleFontColor=PALETTE_GREY))
    save_path = (os.path.join(ROOT_PATH, SAVE_TMP_PATH, f'{group_id}_help.png'))
    helpCards.generateImage(save_path)
    return save_path
class ShowStatus(StandardPlugin): 
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg in ['-test status', '-test']
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        send(target, 'status: online\n'+VERSION_TXT,data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'ShowStatus',
            'description': '展示状态',
            'commandDescription': '-test/-test status',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }

class ServerMonitor(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg == '-monitor' and data['user_id'] in ROOT_ADMIN_ID
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        statusCards = ResponseImage(
            title = 'Bot 服务器状态', 
            titleColor = PALETTE_CYAN,
        )
        mem:float = psutil.virtual_memory().percent
        cpu:float = psutil.cpu_percent()
        statusCards.addCard(
            ResponseImage.RichContentCard(
                raw_content=[
                ('subtitle', '内存占用: '+str(mem)+'%'),
                ('progressBar', mem/100, 'auto'),
                ('subtitle', 'CPU占用: '+str(cpu)+'%'),
                ('progressBar', cpu/100, 'auto'),
            ])
        )
        save_path = os.path.join(SAVE_TMP_PATH, 'server_monitor.png')
        statusCards.generateImage(save_path)
        save_path = save_path if os.path.isabs(save_path) else os.path.join(ROOT_PATH, save_path)
        send(target, '[CQ:image,file=files:///%s]'%save_path ,data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'ServerMonitor',
            'description': '展示服务器状态',
            'commandDescription': '-monitor',
            'usePlace': ['group', 'private', ],
            'showInHelp': False,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
