import argparse
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from utils.basicConfigs import setConfigs

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
        
import asyncio
import json
from enum import IntEnum

from plugins.autoRepoke import AutoRepoke
from plugins.checkCoins import AddAssignedCoins, CheckCoins, CheckTransactions
from plugins.faq_v2 import AskFAQ, HelpFAQ, MaintainFAQ
from plugins.greetings import MorningGreet, NightGreet
from plugins.groupCalendar import GroupCalendarHelper, GroupCalendarManager
from plugins.hotSearch import BaiduHotSearch, WeiboHotSearch, ZhihuHotSearch
from plugins.news import ShowNews, UpdateNewsAndReport, YesterdayNews
## tmp
from plugins.signIn import SignIn
from plugins.sjmcStatus_v2 import ShowSjmcStatus
from plugins.sjmcStatus_v4 import (McStatusAddServer, McStatusRemoveFooter,
                                   McStatusRemoveServer, McStatusSetFooter,
                                   ShowMcStatus)
from plugins.sjtuInfo import SjtuCanteenInfo, SjtuLibInfo
from plugins.stocks import (BuyStocks, BuyStocksHelper, QueryStocks,
                            QueryStocksHelper, QueryStocksPrice,
                            QueryStocksPriceHelper)
from plugins.superEmoji import (BasketballFace, FirecrackersFace,
                                FireworksFace, HotFace)
from plugins.thanksLUB import ThanksLUB
from utils.accountOperation import create_account_sql
from utils.basicConfigs import (APPLY_GROUP_ID, BACKEND, BACKEND_TYPE,
                                BOT_SELF_QQ)
from utils.basicEvent import (get_group_list, set_friend_add_request,
                              set_group_add_request, warning)
from utils.configAPI import createGlobalConfig, removeInvalidGroupConfigs
from utils.configsLoader import createApplyGroupsSql, loadApplyGroupId
from utils.imageBed import createImageBedSql
from utils.messageChain import MessageChain
from utils.sqlUtils import createBotDataDb
from utils.standardPlugin import (AddGroupStandardPlugin, EmptyAddGroupPlugin,
                                  EmptyPlugin, GuildStandardPlugin,
                                  NotPublishedException, PluginGroupManager,
                                  PokeStandardPlugin, StandardPlugin,
                                  emptyFunction)

try:
    from plugins.mua import (MuaAbstract, MuaAnnEditor, MuaAnnHelper,
                             MuaGroupAnnFilter, MuaGroupBindTarget,
                             MuaGroupUnbindTarget, MuaNotice, MuaQuery,
                             MuaTokenBinder, MuaTokenEmpower, MuaTokenLister,
                             MuaTokenUnbinder, setMuaCredential,
                             startMuaInstanceMainloop)
except NotPublishedException as e:
    print('mua plugins not imported: {}'.format(e))
    MuaAnnHelper, MuaAnnEditor = EmptyPlugin, EmptyPlugin
    MuaTokenBinder, MuaTokenUnbinder, MuaTokenEmpower = EmptyPlugin, EmptyPlugin, EmptyPlugin
    uaTokenLister, MuaNotice, MuaQuery, MuaAbstract = EmptyPlugin, EmptyPlugin, EmptyPlugin, EmptyPlugin
    MuaGroupBindTarget, MuaGroupUnbindTarget = EmptyPlugin, EmptyPlugin
    MuaGroupAnnFilter = EmptyPlugin
    MuaTokenLister = EmptyPlugin
    startMuaInstanceMainloop, setMuaCredential = emptyFunction, emptyFunction
from plugins.BilibiliApiV3 import BilibiliSubscribe, BilibiliSubscribeHelper
from plugins.groupBan import BanImplement, GetBanList, GroupBan, UserBan
from plugins.help_v2 import CheckStatus, ServerMonitor, ShowHelp, ShowStatus
from plugins.lottery import LotteryPlugin
from plugins.privateControl import (GroupApply, HelpInGroup, LsGroup,
                                    PrivateControl)
from plugins.roulette import RoulettePlugin

try:
    from plugins.chatWithNLP import ChatWithNLP
except Exception as e:
    ChatWithNLP = EmptyPlugin
    print('ChatWithNLP not imported: {}'.format(e))
from plugins.abstract import MakeAbstract
from plugins.addGroupRecorder import AddGroupRecorder
from plugins.bilibiliLive import BilibiliLiveMonitor, GetBilibiliLive
from plugins.canvasSync import CanvasiCalBind, CanvasiCalUnbind, GetCanvas
from plugins.cchess import ChineseChessHelper, ChineseChessPlugin
from plugins.charPic import CharPic
from plugins.chatWithAnswerbook import ChatWithAnswerbook
from plugins.chess import ChessHelper, ChessPlugin
from plugins.clearRecord import ClearRecord, RestoreRecord
from plugins.deprecated.sjmcLive import GetSjmcLive
from plugins.eavesdrop import Eavesdrop
from plugins.emojiKitchen import EmojiKitchen
from plugins.fileRecorder import GroupFileRecorder
from plugins.getJwc import (GetJwc, GetSjtuNews,  # , SubscribeJwc
                            SjtuJwcMonitor)
from plugins.getPermission import (AddGroupAdminToBotAdmin, AddPermission,
                                   DelPermission, GetPermission,
                                   ShowPermission)
# from plugins.advertisement import McAdManager
from plugins.groupActReport import (ActRankPlugin, ActReportPlugin,
                                    YourActReportPlugin)
from plugins.groupWordCloud import (GenPersonWordCloud, GenWordCloud,
                                    wordCloudPlugin)
from plugins.handle import Handle, HandleHelper
from plugins.leetcode import LeetcodeReport, ShowLeetcode
from plugins.makeJoke import MakeJoke
from plugins.mathler import Mathler, MathlerHelper
# from plugins.goBang import GoBangPlugin
from plugins.messageRecorder import GroupMessageRecorder
from plugins.notPublished.getMddStatus import (GetMddStatus,  # , SubscribeMdd
                                               MonitorMddStatus)
from plugins.notPublished.jile import Chai_Jile, Yuan_Jile
from plugins.randomNum import RandomNum, ThreeKingdomsRandom
from plugins.tarotCards import TarotCards
from plugins.sendLike import SendLike
from plugins.sjtuActivity import SjtuActivity, SjtuDektMonitor
from plugins.sjtuBwc import SjtuBwc, SjtuBwcMonitor
from plugins.sjtuClassroom import (SjtuClassroom, SjtuClassroomPeopleNum,
                                   SjtuClassroomRecommend, SjtuJsQuery)
from plugins.sjtuClassroomRecorder import (DrawClassroomPeopleCount,
                                           SjtuClassroomRecorder)
from plugins.sjtuElectromobileCharge import GetSjtuCharge
from plugins.sjtuSchoolGate import SjtuSchoolGate
from plugins.uniAgenda import GetUniAgenda
from plugins.wordle import Wordle, WordleHelper
# from plugins.song import ChooseSong # API坏了
from plugins.zsmCorups import ZsmGoldSentence
from plugins.bzCorups import BzGoldSentence

try:
    from plugins.notPublished.EE0502 import ShowEE0502Comments
except NotPublishedException as e:
    ShowEE0502Comments = EmptyPlugin
    print('ShowEE0502Comments not imported: {}'.format(e))

try:
    from plugins.notPublished.sjtuPlusGroupingVerication import \
        SjtuPlusGroupingVerify
except NotPublishedException as e:
    SjtuPlusGroupingVerify = EmptyAddGroupPlugin
    print('SjtuPlusGroupingVerify not imported: {}'.format(e))

try:
    from plugins.notPublished.smpParkourRank import SMPParkourRank
except NotPublishedException as e:
    SMPParkourRank = EmptyAddGroupPlugin
    print('SMPParkourRank not imported: {}'.format(e))
    
from plugins.gocqWatchDog import GocqWatchDog
from plugins.notPublished.sjtuSql import (SearchSjtuSql, SearchSjtuSqlAll,
                                          SearchSjtuSqlAllPrivate,
                                          SearchSjtuSqlPIC)
from plugins.notPublished.sjtuSqlGroupingVerication import \
    SjtuSqlGroupingVerify
from plugins.test import TestLagrange

###### end not published plugins

def sqlInit():
    createBotDataDb()
    createApplyGroupsSql()
    createGlobalConfig()
    create_account_sql()
    createImageBedSql()
    
    loadApplyGroupId()
    # removeInvalidGroupConfigs() # it may danger, consider change it to add tag

sqlInit() # put this after import

ROOT_PATH = os.path.dirname(os.path.realpath(__file__))
RESOURCES_PATH = os.path.join(ROOT_PATH, "resources")

# 根据config初始化
cchessConfig = {}
bilibiliSubscribe = EmptyPlugin()
bilibiliSubscribeHelper = EmptyPlugin()
watchdogMail = None
chaiJile = EmptyPlugin()
yuanJile = EmptyPlugin()
getMddStatus = EmptyPlugin()
monitorMddStatus = EmptyPlugin()
sjtuActivity = EmptyPlugin()
sjtuDektMonitor = EmptyPlugin()
getSjtuCharge = EmptyPlugin()
sjtuPlusGroups = []

if isinstance(config, dict):
    pluginConfigs:Optional[Dict[str, Any]] = config.get('plugins', None)
    if pluginConfigs != None:
        # mua plugin
        if 'mua' in pluginConfigs.keys():
            print('[INFO] 开启MUA插件组')
            muaConfig = pluginConfigs['mua']
            setMuaCredential(muaConfig['BOT_MUA_ID'], muaConfig['BOT_MUA_TOKEN'], muaConfig['MUA_URL'])
            startMuaInstanceMainloop()
        else:
            print('[WARNING] MUA插件组未开启')
        if "cchess" in pluginConfigs.keys():
            print("[INFO] 开启cchess软件")
            cchessConfig = pluginConfigs['cchess']
        else:
            print("[WARNING] cchess软件未配置")
        if "bilibili" in pluginConfigs.keys():
            bilibiliSubscribe = BilibiliSubscribe(pluginConfigs['bilibili']['credential'])
            bilibiliSubscribeHelper = BilibiliSubscribeHelper()
            print("[INFO] 开启bilibili订阅插件")
        else:
            print("[WARNING] bilibili订阅插件未开启")
        if "watchdog" in pluginConfigs.keys():
            watchdogMail = pluginConfigs["watchdog"]
        if "jile" in pluginConfigs.keys():
            chaiJile = Chai_Jile(pluginConfigs["jile"]["chai_qq"])
            yuanJile = Yuan_Jile(pluginConfigs["jile"]["yuan_qq"])
            print("[INFO] 开启jile插件")
        else:
            print("[WARNING] jile插件未开启")
        if "mdd" in pluginConfigs.keys():
            getMddStatus = GetMddStatus(pluginConfigs["mdd"]["mdd_url"], pluginConfigs["mdd"]["mdd_headers"])
            monitorMddStatus = MonitorMddStatus(pluginConfigs["mdd"]["mdd_url"], pluginConfigs["mdd"]["mdd_headers"])
            print("[INFO] 开启mdd插件")
        else:
            print('[WARNING] mdd插件未开启')
        if "sjtu_dekt_v2" in pluginConfigs.keys():
            sjtuActivity = SjtuActivity(pluginConfigs["sjtu_dekt_v2"]["JAC_COOKIE"],pluginConfigs["sjtu_dekt_v2"]["client_id"])
            sjtuDektMonitor = SjtuDektMonitor(pluginConfigs["sjtu_dekt_v2"]["JAC_COOKIE"],pluginConfigs["sjtu_dekt_v2"]["client_id"])
            print("[INFO] 开启sjtu第二课堂插件")
        else:
            print("[WARNING] sjtu第二课堂插件未开启")
        if "add_group_verify" in pluginConfigs.keys():
            for cfg in pluginConfigs["add_group_verify"]["groups"]:
                sjtuPlusGroups.append(SjtuPlusGroupingVerify(
                    cfg['sjtu_plus_key'], cfg['api_name'], cfg['groups_qq']
                ))
        if "sjtu_electron_mobile" in pluginConfigs.keys():
            cfg = pluginConfigs["sjtu_electron_mobile"]
            getSjtuCharge = GetSjtuCharge(cfg["JAC_COOKIE"], cfg["client_id"], cfg["url"])
            print("[INFO] 开启sjtu电动车充电信息插件")
        else:
            print("[WARNING] sjtu电动车充电信息插件未开启")
            
        # if 'xxx' in in pluginConfigs.keys():

# 特殊插件需要复用的放在这里
helper = ShowHelp() # 帮助插件
helperForPrivateControl = HelpInGroup() # BOT管理员查看群聊功能开启情况插件
if watchdogMail != None:
    gocqWatchDog = GocqWatchDog(60, mail_user=watchdogMail['mail_user'], mail_pass=watchdogMail['mail_pass'])
else:
    gocqWatchDog = None
groupMessageRecorder = GroupMessageRecorder() # 群聊消息记录插件
sjtuClassroomRecorder = SjtuClassroomRecorder()
banImpl = BanImplement()


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
    PluginGroupManager([ShowNews(), YesterdayNews(), 
                        PluginGroupManager([UpdateNewsAndReport(), ], 'newsreport')],'news'),  # 新闻
    PluginGroupManager([WeiboHotSearch(), BaiduHotSearch(), ZhihuHotSearch(),], 'hotsearch'),
    PluginGroupManager([SjtuCanteenInfo(),SjtuLibInfo(), SjtuClassroom(), SjtuClassroomPeopleNum(),
                        DrawClassroomPeopleCount(), SjtuSchoolGate(), SjtuJsQuery(),
                        SjtuClassroomRecommend(), getMddStatus, getSjtuCharge, sjtuActivity, #SubscribeMdd(), # 交大餐厅, 图书馆, 核酸点, 麦当劳
                        PluginGroupManager([monitorMddStatus], 'mddmonitor'),
                        PluginGroupManager([sjtuDektMonitor], 'dektmonitor'),], 'sjtuinfo'), 
    # PluginGroupManager([QueryStocksHelper(), QueryStocks(), BuyStocksHelper(), BuyStocks(), QueryStocksPriceHelper(), QueryStocksPrice()],'stocks'), # 股票
    PluginGroupManager([chaiJile, yuanJile],'jile'), # 柴/元神寄了
    PluginGroupManager([SignIn(), ], 'signin'),  # 签到
    PluginGroupManager([ShowSjmcStatus(), GetSjmcLive(), GetBilibiliLive(24716629, '基岩社', '-fdmclive'), SMPParkourRank(),
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
                        SjtuJwcMonitor(), GetSjtuNews(),# jwc服务, jwc广播, 交大新闻
                        PluginGroupManager([SjtuBwcMonitor()], 'bwcreport'),], 'jwc'), 
    PluginGroupManager([RoulettePlugin()],'roulette'), # 轮盘赌
    PluginGroupManager([LotteryPlugin()],'lottery'), # 彩票 TODO
    # PluginGroupManager([GoBangPlugin()],'gobang'),
    PluginGroupManager([ChatWithAnswerbook(), ChatWithNLP()], 'chat'), # 答案之书/NLP
    PluginGroupManager([GetCanvas(), GetUniAgenda(), CanvasiCalBind(), CanvasiCalUnbind()], 'canvas'), # 日历馈送
    # PluginGroupManager([DropOut()], 'dropout'), # 一键退学
    PluginGroupManager([ShowEE0502Comments(), ZsmGoldSentence(), BzGoldSentence(), MakeAbstract()], 'izf'), # 张峰
    PluginGroupManager([ActReportPlugin(), YourActReportPlugin(), ActRankPlugin(), wordCloudPlugin(),
                        ClearRecord(), RestoreRecord(), GenPersonWordCloud(),
                        PluginGroupManager([GenWordCloud()], 'wcdaily')], 'actreport'), #水群报告
    PluginGroupManager([RandomNum(), ThreeKingdomsRandom(), TarotCards()], 'random'),
    PluginGroupManager([bilibiliSubscribeHelper, bilibiliSubscribe], 'bilibili'),
    PluginGroupManager([ChineseChessPlugin(cchessConfig.get('engine_type', 'uci'),
                                           cchessConfig.get('engine_path', None),
                                           cchessConfig.get('engine_options', {})), ChineseChessHelper()], 'cchess'),
    PluginGroupManager([ChessPlugin(), ChessHelper()], 'chess'),
    PluginGroupManager([Wordle(), WordleHelper(), Handle(), HandleHelper(), Mathler(), MathlerHelper()], 'wordle'),
    PluginGroupManager([CharPic(), GroupBan(),
                        GetBilibiliLive(22797301, 'SJTU计算机系', '-sjcs'),
                        BilibiliLiveMonitor(22797301,'SJTU计算机系', 'test'),
                        TestLagrange()], 'test'),
    PluginGroupManager([EmojiKitchen()], 'emoji'),
    PluginGroupManager([ShowLeetcode(), LeetcodeReport()], 'leetcode'),
    PluginGroupManager([SendLike()], 'likes'),
    SearchSjtuSql(), SearchSjtuSqlAll(), SearchSjtuSqlPIC(),
]
PrivatePluginList:List[StandardPlugin]=[ # 私聊启用插件
    helper, ThanksLUB(), CheckStatus(GroupPluginList),
    ShowStatus(),ServerMonitor(),
    LsGroup(), GroupApply(), PrivateControl(), helperForPrivateControl,
    CheckCoins(),AddAssignedCoins(),CheckTransactions(),
    ShowNews(), YesterdayNews(),
    MorningGreet(), NightGreet(),
    SignIn(), SendLike(),
    QueryStocksHelper(), QueryStocks(), BuyStocksHelper(), BuyStocks(), QueryStocksPriceHelper(), QueryStocksPrice(),
    SjtuCanteenInfo(),SjtuLibInfo(),ShowSjmcStatus(),GetJwc(), SjtuBwc(), getSjtuCharge, sjtuActivity,#SubscribeJwc(), 
    MuaAbstract(), MuaQuery(), MuaAnnHelper(), MuaAnnEditor(), 
    MuaTokenBinder(), MuaTokenUnbinder(), MuaTokenEmpower(), MuaTokenLister(),
    GetSjtuNews(),
    LotteryPlugin(),
    GetCanvas(), CanvasiCalBind(), CanvasiCalUnbind(), GetUniAgenda(),
    ShowEE0502Comments(), ZsmGoldSentence(), BzGoldSentence(),
    GetSjmcLive(), GetBilibiliLive(24716629, '基岩社', '-fdmclive'),
    getMddStatus, #SubscribeMdd(),
    SearchSjtuSqlAllPrivate(),
    RandomNum(), ThreeKingdomsRandom(), TarotCards(),
    EmojiKitchen(),
    # ChooseSong(),
    SjtuJsQuery(),
    SjtuClassroom(), SjtuClassroomPeopleNum(), SjtuClassroomRecommend(), DrawClassroomPeopleCount(), SjtuSchoolGate(),
]
GuildPluginList:List[GuildStandardPlugin] = []
GroupPokeList:List[PokeStandardPlugin] = [
    AutoRepoke(), # 自动回复拍一拍
]
AddGroupVerifyPluginList:List[AddGroupStandardPlugin] = [
    AddGroupRecorder(), # place this plugin to the first place
    *sjtuPlusGroups,
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
        if gocqWatchDog != None:
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
    if gocqWatchDog != None:
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
