import os
import argparse
import json
from utils.basicConfigs import setConfigs
from typing import List, Tuple, Any, Dict, Optional
config:Optional[Dict[str, Any]] = None
if __name__ == '__main__':
    # 为了兼容之前的代码这么写的，太丑了，下次一定重构
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, required=False, default=None)
    args = parser.parse_args()
    if args.config != None:
        with open(args.config, 'r') as f:
            config = json.load(f)
        setConfigs(config)
        
import asyncio, json
from enum import IntEnum
from utils.standardPlugin import NotPublishedException
from utils.basicConfigs import APPLY_GROUP_ID, BACKEND, BACKEND_TYPE, BOT_SELF_QQ
from utils.configsLoader import createApplyGroupsSql, loadApplyGroupId
from utils.accountOperation import create_account_sql
from utils.standardPlugin import (
    StandardPlugin, PluginGroupManager, EmptyPlugin, emptyFunction,
    PokeStandardPlugin, AddGroupStandardPlugin, 
    EmptyAddGroupPlugin,GuildStandardPlugin
)
from utils.sqlUtils import createBotDataDb
from utils.configAPI import createGlobalConfig, removeInvalidGroupConfigs
from utils.basicEvent import get_group_list, warning, set_friend_add_request, set_group_add_request
from utils.messageChain import MessageChain

from plugins.autoRepoke import AutoRepoke
from plugins.faq_v2 import MaintainFAQ, AskFAQ, HelpFAQ
from plugins.groupCalendar import GroupCalendarHelper, GroupCalendarManager
from plugins.greetings import MorningGreet, NightGreet
from plugins.checkCoins import CheckCoins, AddAssignedCoins, CheckTransactions
from plugins.superEmoji import FirecrackersFace, FireworksFace, BasketballFace, HotFace
from plugins.news import ShowNews, YesterdayNews, UpdateNewsAndReport
from plugins.hotSearch import WeiboHotSearch, BaiduHotSearch, ZhihuHotSearch
## tmp
from plugins.signIn_v2 import SignIn
try:
    from resources.api.getMddTea24 import IcokeUserBind
except:
    IcokeUserBind = EmptyPlugin
    
from plugins.thanksLUB import ThanksLUB
from plugins.stocks import QueryStocksHelper, QueryStocks, BuyStocksHelper, BuyStocks, QueryStocksPriceHelper, QueryStocksPrice
from plugins.sjtuInfo import SjtuCanteenInfo, SjtuLibInfo
from plugins.sjmcStatus_v2 import ShowSjmcStatus
from plugins.sjmcStatus_v4 import ShowMcStatus, McStatusAddServer, McStatusRemoveServer, McStatusSetFooter, McStatusRemoveFooter
try:
    from plugins.mua import (MuaAnnHelper, MuaAnnEditor, 
        MuaTokenBinder, MuaTokenUnbinder, MuaTokenEmpower,
        MuaTokenLister, MuaNotice, MuaQuery, MuaAbstract,
        MuaGroupBindTarget, MuaGroupUnbindTarget, MuaGroupAnnFilter, 
        startMuaInstanceMainloop, setMuaCredential)
except NotPublishedException as e:
    print('mua plugins not imported: {}'.format(e))
    MuaAnnHelper, MuaAnnEditor = EmptyPlugin, EmptyPlugin
    MuaTokenBinder, MuaTokenUnbinder, MuaTokenEmpower = EmptyPlugin, EmptyPlugin, EmptyPlugin
    uaTokenLister, MuaNotice, MuaQuery, MuaAbstract = EmptyPlugin, EmptyPlugin, EmptyPlugin, EmptyPlugin
    MuaGroupBindTarget, MuaGroupUnbindTarget = EmptyPlugin, EmptyPlugin
    MuaGroupAnnFilter = EmptyPlugin
    MuaTokenLister = EmptyPlugin
    startMuaInstanceMainloop, setMuaCredential = emptyFunction, emptyFunction
from plugins.roulette import RoulettePlugin
from plugins.lottery import LotteryPlugin
from plugins.show2cyPic import Show2cyPIC, ShowSePIC
from plugins.help_v2 import ShowHelp, ShowStatus, ServerMonitor
from plugins.groupBan import GroupBan, UserBan, BanImplement, GetBanList
from plugins.privateControl import PrivateControl, LsGroup, GroupApply, HelpInGroup
from plugins.bilibiliSubscribe_v2 import BilibiliSubscribe, BilibiliSubscribeHelper
try:
    from plugins.chatWithNLP import ChatWithNLP
except NotPublishedException as e:
    ChatWithNLP = EmptyPlugin
    print('ChatWithNLP not imported: {}'.format(e))
from plugins.chatWithAnswerbook import ChatWithAnswerbook
try:
    from plugins.getDekt_v2 import SjtuDekt, SjtuDektMonitor
except NotPublishedException as e:
    SjtuDekt, SjtuDektMonitor = EmptyPlugin, EmptyPlugin
    print('SjtuDekt, SjtuDektMonitor not imported: {}'.format(e))
from plugins.getJwc import GetSjtuNews, GetJwc, SjtuJwcMonitor#, SubscribeJwc
from plugins.sjtuSchoolGate import SjtuSchoolGate
from plugins.sjtuBwc import SjtuBwc, SjtuBwcMonitor
from plugins.canvasSync import CanvasiCalBind, CanvasiCalUnbind, GetCanvas
from plugins.getPermission import GetPermission, AddPermission, DelPermission, ShowPermission, AddGroupAdminToBotAdmin
# from plugins.goBang import GoBangPlugin
from plugins.messageRecorder import GroupMessageRecorder
from plugins.addGroupRecorder import AddGroupRecorder
from plugins.fileRecorder import GroupFileRecorder
from plugins.bilibiliLive import GetBilibiliLive, BilibiliLiveMonitor
from plugins.deprecated.sjmcLive import GetSjmcLive
# from plugins.advertisement import McAdManager
from plugins.groupActReport import ActReportPlugin, ActRankPlugin, YourActReportPlugin
from plugins.groupWordCloud import wordCloudPlugin, GenWordCloud, GenPersonWordCloud
from plugins.randomNum import TarotRandom, RandomNum, ThreeKingdomsRandom
from plugins.sjtuClassroom import SjtuClassroom, SjtuClassroomRecommend, SjtuClassroomPeopleNum
from plugins.sjtuClassroomRecorder import SjtuClassroomRecorder, DrawClassroomPeopleCount
from plugins.makeJoke import MakeJoke
from plugins.uniAgenda import GetUniAgenda
from plugins.chess import ChessPlugin, ChessHelper
from plugins.cchess import ChineseChessPlugin, ChineseChessHelper
# from plugins.song import ChooseSong # API坏了
from plugins.zsmCorups import ZsmGoldSentence
from plugins.clearRecord import ClearRecord, RestoreRecord
from plugins.bilibiliLive import GetBilibiliLive, BilibiliLiveMonitor
from plugins.wordle import Wordle, WordleHelper
from plugins.handle import Handle, HandleHelper
from plugins.emojiKitchen import EmojiKitchen
from plugins.leetcode import ShowLeetcode, LeetcodeReport
from plugins.abstract import MakeAbstract
from plugins.eavesdrop import Eavesdrop
from plugins.moyu import GetMoyuCalendar, UpdateMoyuCalendar
try:
    from plugins.apexStatus import ApexStatusPlugin
except NotPublishedException as e:
    ApexStatusPlugin = EmptyPlugin
try:
    from plugins.niuChaoYue import GetNiuChaoYue, NiuChaoYueMonitor
except NotPublishedException as e:
    GetNiuChaoYue, NiuChaoYueMonitor = EmptyPlugin, EmptyPlugin
try:
    from plugins.notPublished.jile import Chai_Jile, Yuan_Jile
except NotPublishedException as e:
    Chai_Jile = EmptyPlugin
    Yuan_Jile = EmptyPlugin
    print('Chai_Jile, Yuan_Jile not imported: {}'.format(e))
try:
    from plugins.notPublished.getMddStatus import GetMddStatus, MonitorMddStatus#, SubscribeMdd
except NotPublishedException as e:
    GetMddStatus, MonitorMddStatus = EmptyPlugin, EmptyPlugin
    print('GetMddStatus, MonitorMddStatus not imported: {}'.format(e))

try:
    from plugins.notPublished.EE0502 import ShowEE0502Comments
except NotPublishedException as e:
    ShowEE0502Comments = EmptyPlugin
    print('ShowEE0502Comments not imported: {}'.format(e))

try:
    from plugins.notPublished.sjtuPlusGroupingVerication import SjtuPlusGroupingVerify
except NotPublishedException as e:
    SjtuPlusGroupingVerify = EmptyAddGroupPlugin
    print('SjtuPlusGroupingVerify not imported: {}'.format(e))
    
from plugins.gocqWatchDog import GocqWatchDog
from plugins.xhsSubscribe import XhsSubscribe, XhsSubscribeHelper
from plugins.douyinSubscribe import DouyinSubscribe, DouyinSubscribeHelper
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
sjtuClassroomRecorder = SjtuClassroomRecorder()
banImpl = BanImplement()

# 根据config初始化
if isinstance(config, dict):
    pluginConfigs:Optional[Dict[str, Any]] = config.get('plugins', None)
    if pluginConfigs != None:
        # mua plugin
        if 'mua' in pluginConfigs.keys():
            muaConfig = pluginConfigs['mua']
            setMuaCredential(muaConfig['BOT_MUA_ID'], muaConfig['BOT_MUA_TOKEN'], muaConfig['MUA_URL'])
            startMuaInstanceMainloop()
        # if 'xxx' in in pluginConfigs.keys():
        
GroupPluginList:List[StandardPlugin]=[ # 指定群启用插件
    groupMessageRecorder, banImpl, 
    helper,ShowStatus(),ServerMonitor(), # 帮助
    GetPermission(), ThanksLUB(), Eavesdrop(),
    PluginGroupManager([AddPermission(), DelPermission(), ShowPermission(), AddGroupAdminToBotAdmin(),
                        UserBan(banImpl), GetBanList()], 'permission'), # 权限
    PluginGroupManager([AskFAQ(), MaintainFAQ(), HelpFAQ()],'faq'), # 问答库与维护
    PluginGroupManager([GroupCalendarHelper(), GroupCalendarManager()], 'calendar'),
    PluginGroupManager([MorningGreet(), NightGreet()], 'greeting'), # 早安晚安
    PluginGroupManager([CheckCoins(), AddAssignedCoins(),CheckTransactions()],'money'), # 查询金币,查询记录,增加金币（管理员）
    PluginGroupManager([FireworksFace(), FirecrackersFace(), BasketballFace(), HotFace(), MakeJoke()], 'superemoji'), # 超级表情
    PluginGroupManager([ShowNews(), YesterdayNews(), GetMoyuCalendar(),
                        PluginGroupManager([UpdateNewsAndReport(), UpdateMoyuCalendar()], 'newsreport')],'news'),  # 新闻
    PluginGroupManager([WeiboHotSearch(), BaiduHotSearch(), ZhihuHotSearch(),], 'hotsearch'),
    PluginGroupManager([SjtuCanteenInfo(),SjtuLibInfo(), SjtuClassroom(), SjtuClassroomPeopleNum(),
                        DrawClassroomPeopleCount(), SjtuSchoolGate(),
                        SjtuClassroomRecommend(), GetMddStatus(),#IcokeUserBind(), #SubscribeMdd(), # 交大餐厅, 图书馆, 核酸点, 麦当劳
                        PluginGroupManager([MonitorMddStatus()], 'mddmonitor'),],'sjtuinfo'), 
    # PluginGroupManager([QueryStocksHelper(), QueryStocks(), BuyStocksHelper(), BuyStocks(), QueryStocksPriceHelper(), QueryStocksPrice()],'stocks'), # 股票
    PluginGroupManager([Chai_Jile(), Yuan_Jile()],'jile'), # 柴/元神寄了
    PluginGroupManager([SignIn(), IcokeUserBind()], 'signin'),  # 签到
    PluginGroupManager([ShowSjmcStatus(), GetSjmcLive(), GetBilibiliLive(24716629, '基岩社', '-fdmclive'), 
                        PluginGroupManager([BilibiliLiveMonitor(25567444, '交大MC社', 'mclive'),
                                            BilibiliLiveMonitor(24716629, '基岩社', 'mclive'), ], 'mclive'),
                        # PluginGroupManager([McAdManager()], 'mcad')# 新生群mc广告播报
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
    PluginGroupManager([GetJwc(), SjtuBwc(), #SubscribeJwc() ,
                        SjtuJwcMonitor(), GetSjtuNews(), SjtuDekt(),# jwc服务, jwc广播, 交大新闻, 第二课堂
                        PluginGroupManager([SjtuDektMonitor()], 'dekt'),
                        PluginGroupManager([SjtuBwcMonitor()], 'bwcreport'),], 'jwc'), 
    PluginGroupManager([RoulettePlugin()],'roulette'), # 轮盘赌
    PluginGroupManager([LotteryPlugin()],'lottery'), # 彩票 TODO
    # PluginGroupManager([GoBangPlugin()],'gobang'),
    PluginGroupManager([Show2cyPIC()], 'anime'), #ShowSePIC(), # 来点图图，来点涩涩(关闭)
    PluginGroupManager([ChatWithAnswerbook(), ChatWithNLP()], 'chat'), # 答案之书/NLP
    PluginGroupManager([GetCanvas(), GetUniAgenda(), CanvasiCalBind(), CanvasiCalUnbind()], 'canvas'), # 日历馈送
    # PluginGroupManager([DropOut()], 'dropout'), # 一键退学
    PluginGroupManager([ShowEE0502Comments(), ZsmGoldSentence(), MakeAbstract()], 'izf'), # 张峰
    PluginGroupManager([ActReportPlugin(), YourActReportPlugin(), ActRankPlugin(), wordCloudPlugin(),
                        ClearRecord(), RestoreRecord(), GenPersonWordCloud(),
                        PluginGroupManager([GenWordCloud()], 'wcdaily')], 'actreport'), #水群报告
    PluginGroupManager([RandomNum(), ThreeKingdomsRandom(), TarotRandom()], 'random'),
    PluginGroupManager([BilibiliSubscribeHelper(), BilibiliSubscribe()], 'bilibili'),
    PluginGroupManager([ChineseChessPlugin(), ChineseChessHelper()], 'cchess'),
    PluginGroupManager([ChessPlugin(), ChessHelper()], 'chess'),
    PluginGroupManager([ApexStatusPlugin()], 'apex'),
    # PluginGroupManager([ChooseSong()], 'song'),
    PluginGroupManager([Wordle(), WordleHelper(), Handle(), HandleHelper()], 'wordle'),
    PluginGroupManager([GetNiuChaoYue(), NiuChaoYueMonitor(), GroupBan(),
                        GetBilibiliLive(22797301, 'SJTU计算机系', '-sjcs'),
                        BilibiliLiveMonitor(22797301,'SJTU计算机系', 'test')], 'test'),
    PluginGroupManager([EmojiKitchen()], 'emoji'),
    PluginGroupManager([ShowLeetcode(), LeetcodeReport()], 'leetcode'),
    PluginGroupManager([XhsSubscribeHelper(),XhsSubscribe()], 'xhs'),
    PluginGroupManager([DouyinSubscribeHelper(),DouyinSubscribe()], 'douyin'),
    # PluginGroupManager([], 'arxiv'),
]
PrivatePluginList:List[StandardPlugin]=[ # 私聊启用插件
    helper, ThanksLUB(),
    ShowStatus(),ServerMonitor(),
    LsGroup(), GroupApply(), PrivateControl(), helperForPrivateControl,
    CheckCoins(),AddAssignedCoins(),CheckTransactions(),
    ShowNews(), YesterdayNews(),
    MorningGreet(), NightGreet(),
    SignIn(), 
    QueryStocksHelper(), QueryStocks(), BuyStocksHelper(), BuyStocks(), QueryStocksPriceHelper(), QueryStocksPrice(),
    SjtuCanteenInfo(),SjtuLibInfo(),ShowSjmcStatus(),SjtuDekt(),GetJwc(), SjtuBwc(), #SubscribeJwc(), 
    MuaAbstract(), MuaQuery(), MuaAnnHelper(), MuaAnnEditor(), 
    MuaTokenBinder(), MuaTokenUnbinder(), MuaTokenEmpower(), MuaTokenLister(),
    GetSjtuNews(),
    LotteryPlugin(),
    Show2cyPIC(), #ShowSePIC(),
    GetCanvas(), CanvasiCalBind(), CanvasiCalUnbind(), GetUniAgenda(),
    ShowEE0502Comments(), ZsmGoldSentence(),
    GetSjmcLive(), GetBilibiliLive(24716629, '基岩社', '-fdmclive'),
    GetMddStatus(), #SubscribeMdd(),
    RandomNum(), ThreeKingdomsRandom(), TarotRandom(),
    EmojiKitchen(),
    # ChooseSong(),
    SjtuClassroom(), SjtuClassroomPeopleNum(), SjtuClassroomRecommend(), DrawClassroomPeopleCount(), SjtuSchoolGate(),
]
GuildPluginList:List[GuildStandardPlugin] = []
GroupPokeList:List[PokeStandardPlugin] = [
    AutoRepoke(), # 自动回复拍一拍
]
AddGroupVerifyPluginList:List[AddGroupStandardPlugin] = [
    AddGroupRecorder(), # place this plugin to the first place
    SjtuPlusGroupingVerify('dytwzzb',[]),
    SjtuPlusGroupingVerify('test',[]),
]
helper.updatePluginList(GroupPluginList, PrivatePluginList)
helperForPrivateControl.setPluginList(GroupPluginList)

class NoticeType(IntEnum):
    NoProcessRequired = 0
    GroupMessageNoProcessRequired = 1
    GuildMessageNoProcessRequired = 2
    PrivateMessageNoProcessRequired = 3
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
            if json_data['user_id'] == BOT_SELF_QQ:
                return NoticeType.GroupMessageNoProcessRequired
            elif json_data['group_id'] in APPLY_GROUP_ID:
                return NoticeType.GroupMessage
            else:
                return NoticeType.GroupMessageNoProcessRequired
        elif json_data['message_type'] == 'private':
            if json_data['user_id'] == BOT_SELF_QQ:
                return NoticeType.PrivateMessageNoProcessRequired
            else:
                return NoticeType.PrivateMessage
        elif json_data['message_type'] == 'guild':
            if (json_data['guild_id'], json_data['channel_id']) in []:
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

def onMessageReceive(message:str)->str:
    data:Dict[str,Any] = json.loads(message)
    # 筛选并处理指定事件
    flag=eventClassify(data)
    # print(data)
    # 消息格式转换
    if BACKEND == BACKEND_TYPE.LAGRANGE and 'message' in data.keys():
        msgChain = MessageChain(data['message'])
        msgChain.fixLagrangeImgUrl()
        msgOrigin = msgChain.toCqcode()
        msg = msgOrigin.strip()
        data['message_chain'] = data['message']
        data['message'] = msgOrigin
        # print(msg)
    
    if flag==NoticeType.GroupMessage: # 群消息处理
        msg = data['message'].strip()
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
        for event in [GroupFileRecorder()]:
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
        if not p.initCheck():
            print(f'{infoDict} init check failed!')
            exit(1)
        if 'group' not in infoDict['usePlace']:
            print("plugin [{}] can not be used in group talk!".format(infoDict['name']))
            exit(1)
    for p in PrivatePluginList:
        infoDict = p.getPluginInfo()
        if not p.initCheck():
            print(f'{infoDict} init check failed!')
            exit(1)
        if 'private' not in infoDict['usePlace']:
            print("plugin [{}] can not be used in private talk!".format(infoDict['name']))
            exit(1)
    gocqWatchDog.start()

if __name__ == '__main__':
    initCheck()
    if BACKEND == BACKEND_TYPE.GOCQHTTP:
        from flask import Flask, request
        app = Flask(__name__)
        @app.route('/', methods=["POST"])
        def onMsgRecvGocq():
            msg = request.get_data(as_text=True)
            return onMessageReceive(msg)
        if config == None:
            app.run(host="127.0.0.1", port=5986)
        else:
            app.run(host=config['frontend-ip'], port=config['frontend-port'])
    elif BACKEND == BACKEND_TYPE.LAGRANGE:
        from websocket_server import WebsocketServer
        if config == None:
            server = WebsocketServer("127.0.0.1", port=5706)
        else:
            server = WebsocketServer(config['frontend-ip'], port=config['frontend-port'])
        def onMsgRecvLag(_0, _1, msg):
            onMessageReceive(msg)
        server.set_fn_message_received(onMsgRecvLag)
        print('-------------You can start Lagrange Now----------------')
        server.run_forever()
    else:
        print('invalid backend type')