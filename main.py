import os
from flask import Flask, request
from enum import IntEnum
from typing import List, Tuple, Any, Dict
from utils.standard_plugin import NotPublishedException
from utils.basic_configs import APPLY_GROUP_ID, APPLY_GUILD_ID
from utils.configs_loader import create_apply_groups_sql, load_apply_group_id
from utils.account_operation import create_account_sql
from utils.standard_plugin import (
    StandardPlugin, PluginGroupManager, EmptyPlugin,
    PokeStandardPlugin, AddGroupStandardPlugin,
    EmptyAddGroupPlugin, GuildStandardPlugin
)
from utils.sql_utils import create_bot_data_db
from utils.config_api import create_global_config, remove_invalid_group_configs
from utils.basic_event import get_group_list, warning, set_friend_add_request, set_group_add_request

from plugins.auto_repoke import AutoRepoke
from plugins.faq_v2 import MaintainFAQ, AskFAQ, HelpFAQ
from plugins.group_calendar import GroupCalendarHelper, GroupCalendarManager
from plugins.greetings import MorningGreet, NightGreet
from plugins.check_coins import CheckCoins, AddAssignedCoins, CheckTransactions
from plugins.super_emoji import FirecrackersFace, FireworksFace, BasketballFace, HotFace
from plugins.news import ShowNews, YesterdayNews, UpdateNewsAndReport
from plugins.hot_search import WeiboHotSearch, BaiduHotSearch, ZhihuHotSearch
from plugins.sign_in import SignIn
from plugins.thanks_lub import ThanksLUB
from plugins.stocks import QueryStocksHelper, QueryStocks, BuyStocksHelper, BuyStocks, QueryStocksPriceHelper, \
    QueryStocksPrice
from plugins.sjtu_info import SjtuCanteenInfo, SjtuLibInfo
from plugins.sjmc_status_v2 import ShowSjmcStatus
from plugins.sjmc_status_v3 import ShowMcStatus, McStatusAddServer, McStatusRemoveServer, McStatusSetFooter, \
    McStatusRemoveFooter

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
from plugins.show_to_cy_pic import Show2cyPIC, ShowSePIC
from plugins.help_v2 import ShowHelp, ShowStatus, ServerMonitor
from plugins.group_ban import GroupBan, UserBan, BanImplement, GetBanList
from plugins.private_control import PrivateControl, LsGroup, GroupApply, HelpInGroup
from plugins.bilibili_subscribe_v2 import BilibiliSubscribe, BilibiliSubscribeHelper

try:
    from plugins.chat_with_nlp import ChatWithNLP
except NotPublishedException as e:
    ChatWithNLP = EmptyPlugin
    print('ChatWithNLP not imported: {}'.format(e))
from plugins.chat_with_answerbook import ChatWithAnswerbook

try:
    from plugins.get_dekt import SjtuDekt, SjtuDektMonitor
except NotPublishedException as e:
    SjtuDekt, SjtuDektMonitor = EmptyPlugin, EmptyPlugin
    print('SjtuDekt, SjtuDektMonitor not imported: {}'.format(e))
from plugins.get_jwc import GetSjtuNews, GetJwc, SjtuJwcMonitor, GetJwcForGuild  # , SubscribeJwc
from plugins.sjtu_school_gate import SjtuSchoolGate
from plugins.sjtu_bwc import SjtuBwc, SjtuBwcMonitor
from plugins.canvas_sync import CanvasiCalBind, CanvasiCalUnbind, GetCanvas
from plugins.get_permission import GetPermission, AddPermission, DelPermission, ShowPermission, AddGroupAdminToBotAdmin
# from plugins.goBang import GoBangPlugin
from plugins.message_recorder import GroupMessageRecorder
from plugins.add_group_recorder import AddGroupRecorder
from plugins.file_recorder import GroupFileRecorder
from plugins.bilibili_live import GetBilibiliLive, BilibiliLiveMonitor
from plugins.deprecated.sjmc_live import GetSjmcLive
# from plugins.advertisement import McAdManager
from plugins.group_act_report import ActReportPlugin, ActRankPlugin
from plugins.group_word_cloud import wordCloudPlugin, GenWordCloud
from plugins.random_num import TarotRandom, RandomNum, ThreeKingdomsRandom
from plugins.sjtu_classroom import SjtuClassroom, SjtuClassroomRecommend, SjtuClassroomPeopleNum
from plugins.sjtu_classroom_recorder import SjtuClassroomRecorder, DrawClassroomPeopleCount
from plugins.make_joke import MakeJoke
from plugins.uni_agenda import GetUniAgenda
from plugins.chess import ChessPlugin, ChessHelper
from plugins.cchess import ChineseChessPlugin, ChineseChessHelper
from plugins.song import ChooseSong
from plugins.zsm_corups import ZsmGoldSentence
from plugins.apex_status import ApexStatusPlugin
from plugins.clear_record import ClearRecord, RestoreRecord
from plugins.bilibili_live import GetBilibiliLive, BilibiliLiveMonitor

try:
    from plugins.not_published.jile import Chai_Jile, Yuan_Jile
except NotPublishedException as e:
    Chai_Jile = EmptyPlugin
    Yuan_Jile = EmptyPlugin
    print('Chai_Jile, Yuan_Jile not imported: {}'.format(e))
try:
    from plugins.not_published.get_mdd_status import GetMddStatus, MonitorMddStatus  # , SubscribeMdd
except NotPublishedException as e:
    GetMddStatus, MonitorMddStatus = EmptyPlugin, EmptyPlugin
    print('GetMddStatus, MonitorMddStatus not imported: {}'.format(e))

try:
    from plugins.not_published.ee0502 import ShowEE0502Comments
except NotPublishedException as e:
    ShowEE0502Comments = EmptyPlugin
    print('ShowEE0502Comments not imported: {}'.format(e))

try:
    from plugins.not_published.sjtu_plus_grouping_verication import SjtuPlusGroupingVerify
except NotPublishedException as e:
    SjtuPlusGroupingVerify = EmptyAddGroupPlugin
    print('SjtuPlusGroupingVerify not imported: {}'.format(e))

from plugins.gocq_watch_dog import GocqWatchDog


###### end not published plugins

def sql_init():
    create_bot_data_db()
    create_apply_groups_sql()
    create_global_config()
    create_account_sql()

    load_apply_group_id()
    # removeInvalidGroupConfigs() # it may danger, consider change it to add tag


sql_init()  # put this after import

ROOT_PATH = os.path.dirname(os.path.realpath(__file__))
RESOURCES_PATH = os.path.join(ROOT_PATH, "resources")

# 特殊插件需要复用的放在这里
helper = ShowHelp()  # 帮助插件
helperForPrivateControl = HelpInGroup()  # BOT管理员查看群聊功能开启情况插件
gocqWatchDog = GocqWatchDog(60)
groupMessageRecorder = GroupMessageRecorder()  # 群聊消息记录插件
sjtuClassroomRecorder = SjtuClassroomRecorder()
banImpl = BanImplement()
GroupPluginList: List[StandardPlugin] = [  # 指定群启用插件
    groupMessageRecorder, banImpl,
    helper, ShowStatus(), ServerMonitor(),  # 帮助
    GetPermission(), ThanksLUB(),
    PluginGroupManager([AddPermission(), DelPermission(), ShowPermission(), AddGroupAdminToBotAdmin(),
                        UserBan(banImpl), GetBanList()], 'permission'),  # 权限
    PluginGroupManager([AskFAQ(), MaintainFAQ(), HelpFAQ()], 'faq'),  # 问答库与维护
    PluginGroupManager([GroupCalendarHelper(), GroupCalendarManager()], 'calendar'),
    PluginGroupManager([MorningGreet(), NightGreet()], 'greeting'),  # 早安晚安
    PluginGroupManager([CheckCoins(), AddAssignedCoins(), CheckTransactions()], 'money'),  # 查询金币,查询记录,增加金币（管理员）
    PluginGroupManager([FireworksFace(), FirecrackersFace(), BasketballFace(), HotFace(), MakeJoke()], 'superemoji'),
    # 超级表情
    PluginGroupManager([ShowNews(), YesterdayNews(),
                        PluginGroupManager([UpdateNewsAndReport()], 'newsreport')], 'news'),  # 新闻
    PluginGroupManager([WeiboHotSearch(), BaiduHotSearch(), ZhihuHotSearch(), ], 'hotsearch'),
    PluginGroupManager([SjtuCanteenInfo(), SjtuLibInfo(), SjtuClassroom(), SjtuClassroomPeopleNum(),
                        DrawClassroomPeopleCount(), SjtuSchoolGate(),
                        SjtuClassroomRecommend(), GetMddStatus(),
                        # IcokeUserBind(), #SubscribeMdd(), # 交大餐厅, 图书馆, 核酸点, 麦当劳
                        PluginGroupManager([MonitorMddStatus()], 'mddmonitor'), ], 'sjtuinfo'),
    # PluginGroupManager([QueryStocksHelper(), QueryStocks(), BuyStocksHelper(), BuyStocks(), QueryStocksPriceHelper(), QueryStocksPrice()],'stocks'), # 股票
    PluginGroupManager([Chai_Jile(), Yuan_Jile()], 'jile'),  # 柴/元神寄了
    PluginGroupManager([SignIn()], 'signin'),  # 签到
    PluginGroupManager([ShowSjmcStatus(), GetSjmcLive(), GetBilibiliLive(24716629, '基岩社', '-fdmclive'),
                        PluginGroupManager([BilibiliLiveMonitor(25567444, '交大MC社', 'mclive'),
                                            BilibiliLiveMonitor(24716629, '基岩社', 'mclive'), ], 'mclive'),
                        # PluginGroupManager([McAdManager()], 'mcad')# 新生群mc广告播报
                        ], 'sjmc'),  # MC社服务
    PluginGroupManager(
        [ShowMcStatus(), McStatusAddServer(), McStatusRemoveServer(), McStatusSetFooter(), McStatusRemoveFooter()
         ], 'mcs'),  # MC服务器列表for MUA
    PluginGroupManager([MuaQuery(), MuaAbstract(), MuaAnnHelper(), MuaAnnEditor(),
                        MuaTokenBinder(), MuaTokenUnbinder(), MuaTokenEmpower(), MuaTokenLister(),
                        MuaGroupBindTarget(), MuaGroupUnbindTarget(), MuaGroupAnnFilter(),
                        GetBilibiliLive(30539032, 'MUA', '-mualive'),
                        PluginGroupManager([MuaNotice()], 'muanotice'),
                        PluginGroupManager([BilibiliLiveMonitor(30539032, 'MUA', 'mualive'), ], 'mualive'),
                        ], 'mua'),  # MC高校联盟服务
    PluginGroupManager([GetJwc(), SjtuBwc(),  # SubscribeJwc() ,
                        SjtuJwcMonitor(), GetSjtuNews(), SjtuDekt(),  # jwc服务, jwc广播, 交大新闻, 第二课堂
                        PluginGroupManager([SjtuDektMonitor()], 'dekt'),
                        PluginGroupManager([SjtuBwcMonitor()], 'bwcreport'), ], 'jwc'),
    PluginGroupManager([RoulettePlugin()], 'roulette'),  # 轮盘赌
    PluginGroupManager([LotteryPlugin()], 'lottery'),  # 彩票 TODO
    # PluginGroupManager([GoBangPlugin()],'gobang'),
    PluginGroupManager([Show2cyPIC()], 'anime'),  # ShowSePIC(), # 来点图图，来点涩涩(关闭)
    PluginGroupManager([ChatWithAnswerbook(), ChatWithNLP()], 'chat'),  # 答案之书/NLP
    PluginGroupManager([GetCanvas(), GetUniAgenda(), CanvasiCalBind(), CanvasiCalUnbind()], 'canvas'),  # 日历馈送
    # PluginGroupManager([DropOut()], 'dropout'), # 一键退学
    PluginGroupManager([ShowEE0502Comments(), ZsmGoldSentence()], 'izf'),  # 张峰
    PluginGroupManager([ActReportPlugin(), ActRankPlugin(), wordCloudPlugin(), ClearRecord(), RestoreRecord(),
                        PluginGroupManager([GenWordCloud()], 'wcdaily')], 'actreport'),  # 水群报告
    PluginGroupManager([RandomNum(), ThreeKingdomsRandom(), TarotRandom()], 'random'),
    PluginGroupManager([BilibiliSubscribeHelper(), BilibiliSubscribe()], 'bilibili'),
    PluginGroupManager([ChineseChessPlugin(), ChineseChessHelper()], 'cchess'),
    PluginGroupManager([ChessPlugin(), ChessHelper()], 'chess'),
    PluginGroupManager([ApexStatusPlugin()], 'apex'),
    PluginGroupManager([ChooseSong()], 'song'),
]
PrivatePluginList: List[StandardPlugin] = [  # 私聊启用插件
    helper, ThanksLUB(),
    ShowStatus(), ServerMonitor(),
    LsGroup(), GroupApply(), PrivateControl(), helperForPrivateControl,
    CheckCoins(), AddAssignedCoins(), CheckTransactions(),
    ShowNews(), YesterdayNews(),
    MorningGreet(), NightGreet(),
    SignIn(),
    QueryStocksHelper(), QueryStocks(), BuyStocksHelper(), BuyStocks(), QueryStocksPriceHelper(), QueryStocksPrice(),
    SjtuCanteenInfo(), SjtuLibInfo(), ShowSjmcStatus(), SjtuDekt(), GetJwc(), SjtuBwc(),  # SubscribeJwc(),
    MuaAbstract(), MuaQuery(), MuaAnnHelper(), MuaAnnEditor(),
    MuaTokenBinder(), MuaTokenUnbinder(), MuaTokenEmpower(), MuaTokenLister(),
    GetSjtuNews(),
    LotteryPlugin(),
    Show2cyPIC(),  # ShowSePIC(),
    GetCanvas(), CanvasiCalBind(), CanvasiCalUnbind(), GetUniAgenda(),
    ShowEE0502Comments(), ZsmGoldSentence(),
    GetSjmcLive(), GetBilibiliLive(24716629, '基岩社', '-fdmclive'),
    GetMddStatus(),  # SubscribeMdd(),
    RandomNum(), ThreeKingdomsRandom(), TarotRandom(),
    MakeJoke(),
    ChooseSong(),
    SjtuClassroom(), SjtuClassroomPeopleNum(), SjtuClassroomRecommend(), DrawClassroomPeopleCount(), SjtuSchoolGate(),
]
GuildPluginList: List[GuildStandardPlugin] = [
    GetJwcForGuild(),  # 教务处
]
GroupPokeList: List[PokeStandardPlugin] = [
    AutoRepoke(),  # 自动回复拍一拍
]
AddGroupVerifyPluginList: List[AddGroupStandardPlugin] = [
    AddGroupRecorder(),  # place this plugin to the first place
    SjtuPlusGroupingVerify('dytwzzb', []),
    SjtuPlusGroupingVerify('test', []),
]
helper.update_plugin_list(GroupPluginList, PrivatePluginList)
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
    AddGroup = 31  # 有人要求加入自己的群
    AddPrivate = 32
    AddGroupInvite = 33  # 有人邀请自己加入新群
    GuildMessage = 41


def event_classify(json_data: dict) -> NoticeType:
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
    flag = event_classify(data)
    # 群消息处理
    if flag == NoticeType.GroupMessage:
        msg = data['message'].strip()
        for event in GroupPluginList:
            event: StandardPlugin
            try:
                if event.judge_trigger(msg, data):
                    ret = event.execute_event(msg, data)
                    if ret != None:
                        return ret
            except TypeError as e:
                warning("type error in main.py: {}\n\n{}".format(e, event))
    elif flag == NoticeType.GroupMessageNoProcessRequired:
        groupMessageRecorder.execute_event(data['message'], data)
    elif flag == NoticeType.GroupRecall:
        for plugin in [groupMessageRecorder]:
            plugin.recallMessage(data)
    # 频道消息处理
    elif flag == NoticeType.GuildMessage:
        msg = data['message'].strip()
        for plugin in GuildPluginList:
            plugin: GuildStandardPlugin
            try:
                if plugin.judge_trigger(msg, data):
                    ret = plugin.execute_event(msg, data)
                    if ret != None:
                        return ret
            except TypeError as e:
                warning("type error in main.py: {}\n\n{}".format(e, plugin))
            except BaseException as e:
                warning('base exception in main.py guild plugin: {}\n\n{}'.format(e, plugin))
    # 私聊消息处理
    elif flag == NoticeType.PrivateMessage:
        # print(data)
        msg = data['message'].strip()
        for event in PrivatePluginList:
            if event.judge_trigger(msg, data):
                if event.execute_event(msg, data) != None:
                    break

    elif flag == NoticeType.AddGroup:
        for p in AddGroupVerifyPluginList:
            if p.judge_trigger(data):
                if p.add_group_verication(data) != None:
                    break
    # 上传文件处理
    elif flag == NoticeType.GroupUpload:
        for event in [GroupFileRecorder()]:
            event.uploadFile(data)
    # 群内拍一拍回拍
    elif flag == NoticeType.GroupPoke:
        for p in GroupPokeList:
            if p.judge_trigger(data):
                if p.poke_message(data) != None:
                    break

    # 自动加好友
    elif flag == NoticeType.AddPrivate:
        set_friend_add_request(data['flag'], True)
    # 自动通过加群邀请
    elif flag == NoticeType.AddGroupInvite:
        set_group_add_request(data['flag'], data['sub_type'], True)
    elif flag == NoticeType.GocqHeartBeat:
        gocqWatchDog.feed()
    return "OK"


def init_check():
    # do some check
    for p in GroupPluginList:
        infoDict = p.get_plugin_info()
        assert 'name' in infoDict.keys() and 'description' in infoDict.keys() \
               and 'commandDescription' in infoDict.keys() and 'usePlace' in infoDict.keys()
        if 'group' not in infoDict['usePlace']:
            print("plugin [{}] can not be used in group talk!".format(infoDict['name']))
            exit(1)
    for p in PrivatePluginList:
        infoDict = p.get_plugin_info()
        assert 'name' in infoDict.keys() and 'description' in infoDict.keys() \
               and 'commandDescription' in infoDict.keys() and 'usePlace' in infoDict.keys()
        if 'private' not in infoDict['usePlace']:
            print("plugin [{}] can not be used in private talk!".format(infoDict['name']))
            exit(1)
    gocqWatchDog.start()


if __name__ == '__main__':
    init_check()
    app.run(host="127.0.0.1", port=5986)
