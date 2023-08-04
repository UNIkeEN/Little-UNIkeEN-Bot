import os
from flask import Flask, request
from enum import IntEnum
from typing import List, Tuple, Any, Dict
from utils.standardPlugin import NotPublishedException
from utils.basicConfigs import APPLY_GROUP_ID, APPLY_GUILD_ID
from utils.accountOperation import create_account_sql
from utils.standardPlugin import (
    StandardPlugin, PluginGroupManager, EmptyPlugin,
    PokeStandardPlugin, AddGroupStandardPlugin, 
    EmptyAddGroupPlugin,GuildStandardPlugin
)
from utils.configAPI import createGlobalConfig
from utils.basicEvent import get_group_list, warning, set_friend_add_request

from plugins.autoRepoke import AutoRepoke
from plugins.faq_v2 import MaintainFAQ, AskFAQ, HelpFAQ, createFaqDb, createFaqTable
from plugins.groupCalendar import GroupCalendarHelper, GroupCalendarManager
from plugins.greetings import MorningGreet, NightGreet
from plugins.checkCoins import CheckCoins, AddAssignedCoins, CheckTransactions
from plugins.superEmoji import FirecrackersFace, FireworksFace, BasketballFace, HotFace
from plugins.news import ShowNews, YesterdayNews, UpdateNewsAndReport
from plugins.hotSearch import WeiboHotSearch, BaiduHotSearch, ZhihuHotSearch
try:
    from plugins.signIn_v2 import SignIn
except:
    print('signin_v2 not imported: {}'.format(e))
    from plugins.signIn import SignIn

from plugins.stocks import QueryStocksHelper, QueryStocks, BuyStocksHelper, BuyStocks, QueryStocksPriceHelper, QueryStocksPrice
from plugins.sjtuInfo import SjtuCanteenInfo, SjtuLibInfo
from plugins.sjmcStatus_v2 import ShowSjmcStatus
from plugins.mua import MuaAnnHelper, MuaAnnEditor, MuaTokenBinder, MuaTokenUnbinder, MuaTokenLister, MuaNotice, MuaQuery, MuaAbstract
from plugins.roulette import RoulettePlugin
from plugins.lottery import LotteryPlugin, createLotterySql
from plugins.show2cyPic import Show2cyPIC, ShowSePIC
from plugins.help_v2 import ShowHelp, ShowStatus, ServerMonitor
from plugins.groupBan import GroupBan
from plugins.privateControl import PrivateControl
from plugins.bilibiliSubscribe import createBilibiliTable, BilibiliSubscribe, BilibiliSubscribeHelper, BilibiliUpSearcher
try:
    from plugins.chatWithNLP import ChatWithNLP
except NotPublishedException as e:
    ChatWithNLP = EmptyPlugin
    print('ChatWithNLP not imported: {}'.format(e))
from plugins.chatWithAnswerbook import ChatWithAnswerbook
try:
    from plugins.getDekt import SjtuDekt, SjtuDektMonitor
except NotPublishedException as e:
    SjtuDekt, SjtuDektMonitor = EmptyPlugin, EmptyPlugin
    print('SjtuDekt, SjtuDektMonitor not imported: {}'.format(e))
from plugins.getJwc import GetSjtuNews, GetJwc, SjtuJwcMonitor, GetJwcForGuild#, SubscribeJwc
from plugins.sjtuSchoolGate import SjtuSchoolGate
from plugins.sjtuBwc import SjtuBwc, SjtuBwcMonitor, createBwcSql
from plugins.canvasSync import CanvasiCalBind, CanvasiCalUnbind, GetCanvas
from plugins.getPermission import GetPermission, AddPermission, DelPermission, ShowPermission, AddGroupAdminToBotAdmin
from plugins.goBang import GoBangPlugin
from plugins.messageRecorder import GroupMessageRecorder
from plugins.addGroupRecorder import AddGroupRecorder
from plugins.fileRecorder import GroupFileRecorder
from plugins.sjmcLive import GetSjmcLive, GetFduMcLive, SjmcLiveMonitor, FduMcLiveMonitor
from plugins.advertisement import McAdManager
from plugins.groupActReport import ActReportPlugin, ActRankPlugin
from plugins.groupWordCloud import wordCloudPlugin, GenWordCloud
from plugins.randomNum import TarotRandom, RandomNum, ThreeKingdomsRandom
from plugins.sjtuClassroom import SjtuClassroom, SjtuClassroomRecommend, SjtuClassroomPeopleNum
from plugins.sjtuClassroomRecorder import SjtuClassroomRecorder, DrawClassroomPeopleCount
from plugins.makeJoke import MakeJoke
from plugins.uniAgenda import GetUniAgenda
from plugins.cchess import ChineseChessPlugin, ChineseChessHelper
from plugins.song import ChooseSong
from plugins.zsmCorups import ZsmGoldSentence
from plugins.apexStatus import ApexStatusPlugin
from plugins.clearRecord import ClearRecord, RestoreRecord
try:
    from resources.api.getMddCola import IcolaUserBind
except:
    print("IcolaUserBind not imported")
    IcolaUserBind = EmptyPlugin
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

###### end not published plugins

def sqlInit():
    createGlobalConfig()
    create_account_sql()
    createFaqDb()
    createBilibiliTable()
    createLotterySql()
    createBwcSql()
    for group in get_group_list():
        groupId = group['group_id']
        createFaqTable(str(groupId))
sqlInit()

ROOT_PATH = os.path.dirname(os.path.realpath(__file__))
RESOURCES_PATH = os.path.join(ROOT_PATH, "resources")

# 特殊插件需要复用的放在这里
helper = ShowHelp() # 帮助插件
gocqWatchDog = GocqWatchDog(60)
groupMessageRecorder = GroupMessageRecorder() # 群聊消息记录插件
sjtuClassroomRecorder = SjtuClassroomRecorder()

GroupPluginList:List[StandardPlugin]=[ # 指定群启用插件
    groupMessageRecorder,
    helper,ShowStatus(),ServerMonitor(), # 帮助
    GetPermission(), 
    PluginGroupManager([AddPermission(), DelPermission(), ShowPermission(), AddGroupAdminToBotAdmin()], 'permission'), # 权限
    PluginGroupManager([AskFAQ(), MaintainFAQ(), HelpFAQ()],'faq'), # 问答库与维护
    PluginGroupManager([GroupCalendarHelper(), GroupCalendarManager()], 'calendar'),
    PluginGroupManager([MorningGreet(), NightGreet()], 'greeting'), # 早安晚安
    PluginGroupManager([CheckCoins(), AddAssignedCoins(),CheckTransactions()],'money'), # 查询金币,查询记录,增加金币（管理员）
    PluginGroupManager([FireworksFace(), FirecrackersFace(), BasketballFace(), HotFace(), MakeJoke()], 'superemoji'), # 超级表情
    PluginGroupManager([ShowNews(), YesterdayNews(), 
                        PluginGroupManager([UpdateNewsAndReport()], 'newsreport')],'news'),  # 新闻
    PluginGroupManager([WeiboHotSearch(), BaiduHotSearch(), ZhihuHotSearch(),], 'hotsearch'),
    PluginGroupManager([SjtuCanteenInfo(),SjtuLibInfo(), SjtuClassroom(), SjtuClassroomPeopleNum(),
                        DrawClassroomPeopleCount(), SjtuSchoolGate(),
                        SjtuClassroomRecommend(), GetMddStatus(), IcolaUserBind(),#IcokeUserBind(), #SubscribeMdd(), # 交大餐厅, 图书馆, 核酸点, 麦当劳
                        PluginGroupManager([MonitorMddStatus()], 'mddmonitor'),],'sjtuinfo'), 
    # PluginGroupManager([QueryStocksHelper(), QueryStocks(), BuyStocksHelper(), BuyStocks(), QueryStocksPriceHelper(), QueryStocksPrice()],'stocks'), # 股票
    PluginGroupManager([Chai_Jile(), Yuan_Jile()],'jile'), # 柴/元神寄了
    PluginGroupManager([SignIn()], 'signin'),  # 签到
    PluginGroupManager([ShowSjmcStatus(), GetSjmcLive(), GetFduMcLive(),
                        PluginGroupManager([SjmcLiveMonitor(),FduMcLiveMonitor()], 'mclive'),
                        PluginGroupManager([McAdManager()], 'mcad')], 'sjmc'), #MC社服务
    PluginGroupManager([MuaQuery(), MuaAbstract(), MuaAnnHelper(), MuaAnnEditor(), MuaTokenBinder(), MuaTokenUnbinder(), MuaTokenLister(),
                        PluginGroupManager([MuaNotice()], 'muanotice')], 'mua'), #MC高校联盟服务
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
    PluginGroupManager([ShowEE0502Comments(), ZsmGoldSentence()], 'izf'), # 张峰
    PluginGroupManager([ActReportPlugin(), ActRankPlugin(), wordCloudPlugin(), ClearRecord(), RestoreRecord(),
                        PluginGroupManager([GenWordCloud()], 'wcdaily')], 'actreport'), #水群报告
    PluginGroupManager([RandomNum(), ThreeKingdomsRandom(), TarotRandom()], 'random'),
    PluginGroupManager([BilibiliSubscribeHelper(), BilibiliSubscribe()], 'bilibili'),
    PluginGroupManager([ChineseChessPlugin(), ChineseChessHelper()], 'cchess'),
    PluginGroupManager([ApexStatusPlugin()], 'apex'),
    PluginGroupManager([ChooseSong()], 'song'),
    PrivateControl(),
]
PrivatePluginList:List[StandardPlugin]=[ # 私聊启用插件
    helper, 
    ShowStatus(),ServerMonitor(),
    CheckCoins(),AddAssignedCoins(),CheckTransactions(),
    ShowNews(), YesterdayNews(),
    MorningGreet(), NightGreet(),
    SignIn(), 
    QueryStocksHelper(), QueryStocks(), BuyStocksHelper(), BuyStocks(), QueryStocksPriceHelper(), QueryStocksPrice(),
    SjtuCanteenInfo(),SjtuLibInfo(),ShowSjmcStatus(),SjtuDekt(),GetJwc(), SjtuBwc(), #SubscribeJwc(), 
    MuaAbstract(), MuaQuery(), MuaAnnHelper(), MuaAnnEditor(), MuaTokenBinder(), MuaTokenUnbinder(), MuaTokenLister(),
    GetSjtuNews(),
    LotteryPlugin(),
    Show2cyPIC(), #ShowSePIC(),
    GetCanvas(), CanvasiCalBind(), CanvasiCalUnbind(), GetUniAgenda(),
    ShowEE0502Comments(), ZsmGoldSentence(),
    GetSjmcLive(), GetFduMcLive(),
    GetMddStatus(), IcolaUserBind(),#SubscribeMdd(),
    RandomNum(), ThreeKingdomsRandom(), TarotRandom(),
    MakeJoke(),
    ChooseSong(),
    SjtuClassroom(), SjtuClassroomPeopleNum(), SjtuClassroomRecommend(), DrawClassroomPeopleCount(), SjtuSchoolGate(),
    PrivateControl(),
]
GuildPluginList:List[GuildStandardPlugin] = [
    GetJwcForGuild(), # 教务处
]
GroupPokeList:List[PokeStandardPlugin] = [
    AutoRepoke(), # 自动回复拍一拍
]
AddGroupVerifyPluginList:List[AddGroupStandardPlugin] = [
    AddGroupRecorder(), # place this plugin to the first place
    SjtuPlusGroupingVerify('dytwzzb',[]),
    SjtuPlusGroupingVerify('test',[]),
]
helper.updatePluginList(GroupPluginList, PrivatePluginList)

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
    AddGroup = 31
    AddPrivate = 32
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
            return NoticeType.AddGroup
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
    app.run(host="127.0.0.1", port=5986)