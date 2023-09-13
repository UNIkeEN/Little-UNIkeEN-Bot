import os
from flask import Flask, request
from enum import IntEnum
from typing import List, Tuple, Any, Dict
from utils.standardPlugin import NotPublishedException
from utils.basicConfigs import APPLY_GROUP_ID, APPLY_GUILD_ID
from utils.configsLoader import createApplyGroupsSql, loadApplyGroupId
from utils.accountOperation import create_account_sql
from utils.standardPlugin import (
    StandardPlugin, PluginGroupManager, EmptyPlugin,
    PokeStandardPlugin, AddGroupStandardPlugin, 
    EmptyAddGroupPlugin,GuildStandardPlugin
)
from utils.sqlUtils import createBotDataDb
from utils.configAPI import createGlobalConfig, removeInvalidGroupConfigs
from utils.basicEvent import get_group_list, warning, set_friend_add_request, set_group_add_request

from plugins.autoRepoke import AutoRepoke
from plugins.faq_v2 import MaintainFAQ, AskFAQ, HelpFAQ
from plugins.groupCalendar import GroupCalendarHelper, GroupCalendarManager
from plugins.greetings import MorningGreet, NightGreet
from plugins.checkCoins import CheckCoins, AddAssignedCoins, CheckTransactions
from plugins.superEmoji import FirecrackersFace, FireworksFace, BasketballFace, HotFace
from plugins.news import ShowNews, YesterdayNews, UpdateNewsAndReport
from plugins.hotSearch import WeiboHotSearch, BaiduHotSearch, ZhihuHotSearch
from plugins.signIn import SignIn
from plugins.sjmcStatus_v2 import ShowSjmcStatus
from plugins.sjmcStatus_v3 import ShowMcStatus, McStatusAddServer, McStatusRemoveServer, McStatusSetFooter, McStatusRemoveFooter
try:
    from plugins.mua import (MuaAnnHelper, MuaAnnEditor, 
        MuaTokenBinder, MuaTokenUnbinder, MuaTokenEmpower,
        MuaTokenLister, MuaNotice, MuaQuery, MuaAbstract,
        MuaGroupBindTarget, MuaGroupUnbindTarget, MuaGroupAnnFilter)
except NotPublishedException as e:
    print('mua plugins not imported: {}'.format(e))
    MuaAnnHelper, MuaAnnEditor = EmptyPlugin, EmptyPlugin
    MuaTokenBinder, MuaTokenUnbinder, MuaTokenEmpower = EmptyPlugin, EmptyPlugin, EmptyPlugin
    uaTokenLister, MuaNotice, MuaQuery, MuaAbstract = EmptyPlugin, EmptyPlugin, EmptyPlugin, EmptyPlugin
    MuaGroupBindTarget, MuaGroupUnbindTarget = EmptyPlugin, EmptyPlugin
    MuaGroupAnnFilter = EmptyPlugin
    MuaTokenLister = EmptyPlugin
from plugins.roulette import RoulettePlugin
from plugins.lottery import LotteryPlugin
from plugins.show2cyPic import Show2cyPIC, ShowSePIC
from plugins.help_v2 import ShowHelp, ShowStatus, ServerMonitor
from plugins.groupBan import GroupBan
from plugins.privateControl import PrivateControl, LsGroup, GroupApply, HelpInGroup
from plugins.bilibiliSubscribe_v2 import BilibiliSubscribe, BilibiliSubscribeHelper
from plugins.chatWithAnswerbook import ChatWithAnswerbook
from plugins.getPermission import GetPermission, AddPermission, DelPermission, ShowPermission, AddGroupAdminToBotAdmin
# from plugins.goBang import GoBangPlugin
from plugins.messageRecorder import GroupMessageRecorder
from plugins.addGroupRecorder import AddGroupRecorder
from plugins.bilibiliLive import GetBilibiliLive, BilibiliLiveMonitor
from plugins.deprecated.sjmcLive import GetSjmcLive
# from plugins.advertisement import McAdManager
from plugins.groupActReport import ActReportPlugin, ActRankPlugin
from plugins.groupWordCloud import wordCloudPlugin, GenWordCloud
from plugins.randomNum import TarotRandom, RandomNum, ThreeKingdomsRandom
from plugins.cchess import ChineseChessPlugin, ChineseChessHelper
from plugins.song import ChooseSong
from plugins.clearRecord import ClearRecord, RestoreRecord
from plugins.bilibiliLive import GetBilibiliLive, BilibiliLiveMonitor
from plugins.gocqWatchDog import GocqWatchDog
###### end not published plugins

def sqlInit():
    createBotDataDb()
    createApplyGroupsSql()
    createGlobalConfig()
    create_account_sql()

    loadApplyGroupId()
    # removeInvalidGroupConfigs() # it may danger, consider change it to add tag

sqlInit() # put this after import

ROOT_PATH = os.path.dirname(os.path.realpath(__file__))
RESOURCES_PATH = os.path.join(ROOT_PATH, "resources")

# 特殊插件需要复用的放在这里
helper = ShowHelp() # 帮助插件
helperForPrivateControl = HelpInGroup() # BOT管理员查看群聊功能开启情况插件
gocqWatchDog = GocqWatchDog(60)
groupMessageRecorder = GroupMessageRecorder() # 群聊消息记录插件
getXjmcBilibili = GetBilibiliLive(30143840, '西交MC团队', '-xjmclive')
getFdmcBilibili = GetBilibiliLive(24716629, '基岩社', '-fdmclive')

GroupPluginList:List[StandardPlugin]=[ # 指定群启用插件
    groupMessageRecorder,
    helper,ShowStatus(),ServerMonitor(), # 帮助
    GetPermission(), 
    PluginGroupManager([AddPermission(), DelPermission(), ShowPermission(), AddGroupAdminToBotAdmin()], 'permission'), # 权限
    PluginGroupManager([AskFAQ(), MaintainFAQ(), HelpFAQ()],'faq'), # 问答库与维护
    PluginGroupManager([GroupCalendarHelper(), GroupCalendarManager()], 'calendar'),
    PluginGroupManager([MorningGreet(), NightGreet()], 'greeting'), # 早安晚安
    PluginGroupManager([CheckCoins(), AddAssignedCoins(),CheckTransactions()],'money'), # 查询金币,查询记录,增加金币（管理员）
    PluginGroupManager([FireworksFace(), FirecrackersFace(), BasketballFace(), HotFace(), ], 'superemoji'), # 超级表情
    PluginGroupManager([ShowNews(), YesterdayNews(), 
                        PluginGroupManager([UpdateNewsAndReport()], 'newsreport')],'news'),  # 新闻
    PluginGroupManager([WeiboHotSearch(), BaiduHotSearch(), ZhihuHotSearch(),], 'hotsearch'),
    PluginGroupManager([SignIn()], 'signin'),  # 签到
    PluginGroupManager([ShowSjmcStatus(), GetSjmcLive(), getFdmcBilibili, getXjmcBilibili, 
                        PluginGroupManager([BilibiliLiveMonitor(25567444, '交大MC社', 'mclive'),
                                            BilibiliLiveMonitor(24716629, '基岩社', 'mclive'),
                                            BilibiliLiveMonitor(30143840, '西交MC团队', 'mclive')], 'mclive'),
                        ], 'sjmc'), #MC社服务
    PluginGroupManager([ShowMcStatus(), McStatusAddServer(), McStatusRemoveServer(), McStatusSetFooter(), McStatusRemoveFooter()
                        ], 'mcs'), #MC服务器列表for MUA
    PluginGroupManager([MuaQuery(), MuaAbstract(), MuaAnnHelper(), MuaAnnEditor(), 
                        MuaTokenBinder(), MuaTokenUnbinder(), MuaTokenEmpower(), MuaTokenLister(),
                        MuaGroupBindTarget(), MuaGroupUnbindTarget(), MuaGroupAnnFilter(),
                        GetBilibiliLive(30539032, 'MUA', '-mualive'),
                        PluginGroupManager([MuaNotice()], 'muanotice'),
                        PluginGroupManager([BilibiliLiveMonitor(30539032, 'MUA', 'mualive'),], 'mualive'),
                        ], 'mua'), #MC高校联盟服务
    PluginGroupManager([RoulettePlugin()],'roulette'), # 轮盘赌
    PluginGroupManager([LotteryPlugin()],'lottery'), # 彩票 TODO
    # PluginGroupManager([GoBangPlugin()],'gobang'),
    PluginGroupManager([Show2cyPIC()], 'anime'), #ShowSePIC(), # 来点图图，来点涩涩(关闭)
    PluginGroupManager([ChatWithAnswerbook(), ], 'chat'), # 答案之书
    # PluginGroupManager([DropOut()], 'dropout'), # 一键退学
    PluginGroupManager([ActReportPlugin(), ActRankPlugin(), wordCloudPlugin(), ClearRecord(), RestoreRecord(),
                        PluginGroupManager([GenWordCloud()], 'wcdaily')], 'actreport'), #水群报告
    PluginGroupManager([RandomNum(), ThreeKingdomsRandom(), TarotRandom()], 'random'),
    PluginGroupManager([BilibiliSubscribeHelper(), BilibiliSubscribe()], 'bilibili'),
    PluginGroupManager([ChineseChessPlugin(), ChineseChessHelper()], 'cchess'),
    PluginGroupManager([ChooseSong()], 'song'),
]
PrivatePluginList:List[StandardPlugin]=[ # 私聊启用插件
    helper, 
    ShowStatus(),ServerMonitor(),
    LsGroup(), GroupApply(), PrivateControl(), helperForPrivateControl,
    CheckCoins(),AddAssignedCoins(),CheckTransactions(),
    ShowNews(), YesterdayNews(),
    MorningGreet(), NightGreet(),
    SignIn(), 
    MuaAbstract(), MuaQuery(), MuaAnnHelper(), MuaAnnEditor(), 
    MuaTokenBinder(), MuaTokenUnbinder(), MuaTokenEmpower(), MuaTokenLister(),
    LotteryPlugin(),
    Show2cyPIC(), #ShowSePIC(),
    GetSjmcLive(), getFdmcBilibili, getXjmcBilibili,
    RandomNum(), ThreeKingdomsRandom(), TarotRandom(),
    ChooseSong(),
]
GuildPluginList:List[GuildStandardPlugin] = [

]
GroupPokeList:List[PokeStandardPlugin] = [
    AutoRepoke(), # 自动回复拍一拍
]
AddGroupVerifyPluginList:List[AddGroupStandardPlugin] = [
    AddGroupRecorder(), # place this plugin to the first place
]
helper.updatePluginList(GroupPluginList, PrivatePluginList)
helperForPrivateControl.setPluginList(GroupPluginList)
app = Flask(__name__)

class NoticeType(IntEnum):
    NoProcessRequired = 0
    GroupMessageNoProcessRequired = 1
    GuildMessageNoProcessRequired = 2
    GocqHeartBeat = 5
    GroupMessage = 11
    GroupPoke = 12
    GroupRecall = 13
    GroupUpload = 14
    PrivateMessage = 21
    PrivatePoke = 22
    PrivateRecall = 23
    AddGroup = 31       # 有人要求加入自己的群
    AddPrivate = 32
    AddGroupInvite = 33 # 有人邀请自己加入新群
    GuildMessage = 41

def eventClassify(json_data: dict)->NoticeType: 
    """事件分类"""
    if json_data['post_type'] == 'meta_event' and json_data['meta_event_type'] == 'heartbeat':
        return NoticeType.GocqHeartBeat
    elif json_data['post_type'] == 'message':
        if json_data['message_type'] == 'group':
            if json_data['group_id'] in APPLY_GROUP_ID:
                return NoticeType.GroupMessage
            else:
                return NoticeType.GroupMessageNoProcessRequired
        elif json_data['message_type'] == 'private':
            return NoticeType.PrivateMessage
        elif json_data['message_type'] == 'guild':
            if (json_data['guild_id'], json_data['channel_id']) in APPLY_GUILD_ID:
                return NoticeType.GuildMessage
            else:
                return NoticeType.GuildMessageNoProcessRequired
    elif json_data['post_type'] == 'notice':
        if json_data['notice_type'] == 'notify':
            if json_data['sub_type'] == "poke":
                if json_data.get('group_id', None) in APPLY_GROUP_ID:
                    return NoticeType.GroupPoke
        elif json_data['notice_type'] == 'group_recall':
            return NoticeType.GroupRecall
        elif json_data['notice_type'] == 'group_upload':
            return NoticeType.GroupUpload
    elif json_data['post_type'] == 'request':
        if json_data['request_type'] == 'friend':
            return NoticeType.AddPrivate
        elif json_data['request_type'] == 'group':
            if json_data['sub_type'] == 'add':
                return NoticeType.AddGroup
            elif json_data['sub_type'] == 'invite':
                return NoticeType.AddGroupInvite
    else:
        return NoticeType.NoProcessRequired

@app.route('/', methods=["POST"])
def post_data():
    # 获取事件上报
    data = request.get_json()
    # 筛选并处理指定事件
    flag=eventClassify(data)
    # 群消息处理
    if flag==NoticeType.GroupMessage: 
        msg=data['message'].strip()
        for event in GroupPluginList:
            event: StandardPlugin
            try:
                if event.judgeTrigger(msg, data):
                    ret = event.executeEvent(msg, data)
                    if ret != None:
                        return ret
            except TypeError as e:
                warning("type error in main.py: {}\n\n{}".format(e, event))
    elif flag == NoticeType.GroupMessageNoProcessRequired:
        groupMessageRecorder.executeEvent(data['message'], data)
    elif flag == NoticeType.GroupRecall:
        for plugin in [groupMessageRecorder]:
            plugin.recallMessage(data)
    # 频道消息处理
    elif flag == NoticeType.GuildMessage:
        msg = data['message'].strip()
        for plugin in GuildPluginList:
            plugin: GuildStandardPlugin
            try:
                if plugin.judgeTrigger(msg, data):
                    ret = plugin.executeEvent(msg, data)
                    if ret != None:
                        return ret
            except TypeError as e:
                warning("type error in main.py: {}\n\n{}".format(e, plugin))
            except BaseException as e:
                warning('base exception in main.py guild plugin: {}\n\n{}'.format(e, plugin))
    # 私聊消息处理
    elif flag == NoticeType.PrivateMessage:
        # print(data)
        msg=data['message'].strip()
        for event in PrivatePluginList:
            if event.judgeTrigger(msg, data):
                if event.executeEvent(msg, data)!=None:
                    break

    elif flag == NoticeType.AddGroup:
        for p in AddGroupVerifyPluginList:
            if p.judgeTrigger(data):
                if p.addGroupVerication(data) != None:
                    break
    # 上传文件处理
    elif flag == NoticeType.GroupUpload:
        for event in []:
            event.uploadFile(data)
    # 群内拍一拍回拍
    elif flag==NoticeType.GroupPoke: 
        for p in GroupPokeList:
            if p.judgeTrigger(data):
                if p.pokeMessage(data)!=None:
                    break
            
    # 自动加好友
    elif flag==NoticeType.AddPrivate:
        set_friend_add_request(data['flag'], True)
    # 自动通过加群邀请
    elif flag==NoticeType.AddGroupInvite:
        set_group_add_request(data['flag'], data['sub_type'], True)
    elif flag==NoticeType.GocqHeartBeat:
        gocqWatchDog.feed()
    return "OK"

def initCheck():
    # do some check
    for p in GroupPluginList:
        infoDict = p.getPluginInfo()
        assert 'name' in infoDict.keys() and 'description' in infoDict.keys() \
            and 'commandDescription' in infoDict.keys() and 'usePlace' in infoDict.keys()
        if 'group' not in infoDict['usePlace']:
            print("plugin [{}] can not be used in group talk!".format(infoDict['name']))
            exit(1)
    for p in PrivatePluginList:
        infoDict = p.getPluginInfo()
        assert 'name' in infoDict.keys() and 'description' in infoDict.keys() \
            and 'commandDescription' in infoDict.keys() and 'usePlace' in infoDict.keys()
        if 'private' not in infoDict['usePlace']:
            print("plugin [{}] can not be used in private talk!".format(infoDict['name']))
            exit(1)
    gocqWatchDog.start()

if __name__ == '__main__':
    initCheck()
    app.run(host="127.0.0.1", port=5701)