import os
import traceback
from flask import Flask, request
from enum import IntEnum

from utils.basicEvent import send
from utils.basicConfigs import *
from utils.standardPlugin import StandardPlugin, PluginGroupManager, EmptyPlugin, PokeStandardPlugin

from plugins.autoRepoke import AutoRepoke
from plugins.faq_v2 import MaintainFAQ, AskFAQ, HelpFAQ, createFaqDb, createFaqTable
from plugins.groupCalendar import GroupCalendarHelper, GroupCalendarManager
from plugins.greetings import MorningGreet, NightGreet
from plugins.checkCoins import CheckCoins, AddAssignedCoins, CheckTransactions
from plugins.superEmoji import FirecrackersFace, FireworksFace, BasketballFace, HotFace
from plugins.news import ShowNews, YesterdayNews, UpdateNewsAndReport
from plugins.hotSearch import WeiboHotSearch, BaiduHotSearch, ZhihuHotSearch
from plugins.signIn import SignIn
from plugins.stocks import *
from plugins.sjtuInfo import SjtuCanteenInfo, SjtuLibInfo
from plugins.sjmcStatus_v2 import ShowSjmcStatus
from plugins.roulette import RoulettePlugin
from plugins.lottery import LotteryPlugin
from plugins.show2cyPic import Show2cyPIC, ShowSePIC
from plugins.help_v2 import ShowHelp, ShowStatus, ServerMonitor
from plugins.groupBan import GroupBan
from plugins.bilibiliSubscribe import createBilibiliTable, BilibiliSubscribe, BilibiliSubscribeHelper, BilibiliUpSearcher
try:
    from plugins.chatWithNLP import ChatWithNLP
except:
    ChatWithNLP = EmptyPlugin
from plugins.chatWithAnswerbook import ChatWithAnswerbook
try:
    from plugins.getDekt import SjtuDekt, SjtuDektMonitor
except:
    SjtuDekt, SjtuDektMonitor = EmptyPlugin, EmptyPlugin
from plugins.getJwc import GetSjtuNews, GetJwc, SjtuJwcMonitor#, SubscribeJwc
from plugins.canvasSync import CanvasiCalBind, CanvasiCalUnbind, GetCanvas
from plugins.getPermission import GetPermission, AddPermission, DelPermission, ShowPermission, AddGroupAdminToBotAdmin
from plugins.goBang import GoBangPlugin
from plugins.messageRecorder import GroupMessageRecorder
from plugins.fileRecorder import GroupFileRecorder
from plugins.sjmcLive import GetSjmcLive, GetFduMcLive, SjmcLiveMonitor, FduMcLiveMonitor
from plugins.sjtuHesuan import SjtuHesuan
from plugins.groupActReport import ActReportPlugin
from plugins.groupWordCloud import wordCloudPlugin, GenWordCloud
from plugins.randomNum import TarotRandom, RandomNum, ThreeKingdomsRandom
from plugins.sjtuClassroom import SjtuClassroom

#### not published plugins ####
# try:
#     from plugins.notPublished.dropOut import DropOut
#     DropOut()
# except:
#     DropOut = EmptyPlugin
try:
    from plugins.notPublished.jile import Chai_Jile, Yuan_Jile
except:
    Chai_Jile = EmptyPlugin
    Yuan_Jile = EmptyPlugin
try:
    from plugins.notPublished.getMddStatus import GetMddStatus, MonitorMddStatus#, SubscribeMdd
    GetMddStatus()
except:
    GetMddStatus, MonitorMddStatus = EmptyPlugin, EmptyPlugin
try:
    from plugins.notPublished.EE0502 import ShowEE0502Comments
    ShowEE0502Comments()
except:
    ShowEE0502Comments = EmptyPlugin
###### end not published plugins

ROOT_PATH = os.path.dirname(os.path.realpath(__file__))
RESOURCES_PATH = os.path.join(ROOT_PATH, "resources")

# 特殊插件需要复用的放在这里
helper = ShowHelp() # 帮助插件
groupMessageRecorder = GroupMessageRecorder() # 群聊消息记录插件


GroupPluginList:List[StandardPlugin]=[ # 指定群启用插件
    groupMessageRecorder,
    helper,ShowStatus(),ServerMonitor(), # 帮助
    GetPermission(), 
    PluginGroupManager([AddPermission(), DelPermission(), ShowPermission(), AddGroupAdminToBotAdmin()], 'permission'), # 权限
    PluginGroupManager([AskFAQ(), MaintainFAQ(), HelpFAQ()],'faq'), # 问答库与维护
    PluginGroupManager([GroupCalendarHelper(), GroupCalendarManager()], 'calendar'),
    PluginGroupManager([MorningGreet(), NightGreet()], 'greeting'), # 早安晚安
    PluginGroupManager([CheckCoins(), AddAssignedCoins(),CheckTransactions()],'money'), # 查询金币,查询记录,增加金币（管理员）
    PluginGroupManager([FireworksFace(), FirecrackersFace(), BasketballFace(), HotFace()], 'superemoji'), # 超级表情
    PluginGroupManager([ShowNews(), YesterdayNews(), 
                        PluginGroupManager([UpdateNewsAndReport()], 'newsreport')],'news'),  # 新闻
    PluginGroupManager([WeiboHotSearch(), BaiduHotSearch(), ZhihuHotSearch(),], 'hotsearch'),
    PluginGroupManager([SignIn()], 'signin'),  # 签到
    # PluginGroupManager([QueryStocksHelper(), QueryStocks(), BuyStocksHelper(), BuyStocks(), QueryStocksPriceHelper(), QueryStocksPrice()],'stocks'), # 股票
    PluginGroupManager([Chai_Jile(), Yuan_Jile()],'jile'), # 柴/元神寄了
    PluginGroupManager([SjtuCanteenInfo(),SjtuLibInfo(), SjtuClassroom(), GetMddStatus(), #SubscribeMdd(), # 交大餐厅, 图书馆, 核酸点, 麦当劳
                        PluginGroupManager([MonitorMddStatus()], 'mddmonitor'),],'sjtuinfo'), 
    PluginGroupManager([ShowSjmcStatus(), GetSjmcLive(), GetFduMcLive(),
                        PluginGroupManager([SjmcLiveMonitor(),FduMcLiveMonitor()], 'mclive')], 'sjmc'), #MC社服务
    PluginGroupManager([GetJwc(), #SubscribeJwc() ,
                        SjtuJwcMonitor(), GetSjtuNews(), SjtuDekt(),# jwc服务, jwc广播, 交大新闻, 第二课堂
                        PluginGroupManager([SjtuDektMonitor()], 'dekt')], 'jwc'), 
    PluginGroupManager([RoulettePlugin()],'roulette'), # 轮盘赌
    PluginGroupManager([LotteryPlugin()],'lottery'), # 彩票 TODO
    # PluginGroupManager([GoBangPlugin()],'gobang'),
    PluginGroupManager([Show2cyPIC()], 'anime'), #ShowSePIC(), # 来点图图，来点涩涩(关闭)
    PluginGroupManager([ChatWithAnswerbook(), ChatWithNLP()], 'chat'), # 答案之书/NLP
    PluginGroupManager([GetCanvas(), CanvasiCalBind(), CanvasiCalUnbind()], 'canvas'), # 日历馈送
    # PluginGroupManager([DropOut()], 'dropout'), # 一键退学
    PluginGroupManager([ShowEE0502Comments()], 'izf'), # 张峰
    PluginGroupManager([ActReportPlugin(), wordCloudPlugin(), PluginGroupManager([GenWordCloud()], 'wcdaily')], 'actreport'), #水群报告
    PluginGroupManager([RandomNum(), ThreeKingdomsRandom(), TarotRandom()], 'random'),
    PluginGroupManager([BilibiliSubscribeHelper(), BilibiliSubscribe()], 'bilibili'),
]
PrivatePluginList:List[StandardPlugin]=[ # 私聊启用插件
    helper, 
    ShowStatus(),ServerMonitor(),
    CheckCoins(),AddAssignedCoins(),CheckTransactions(),
    ShowNews(), YesterdayNews(),
    MorningGreet(), NightGreet(),
    SignIn(),
    QueryStocksHelper(), QueryStocks(), BuyStocksHelper(), BuyStocks(), QueryStocksPriceHelper(), QueryStocksPrice(),
    SjtuCanteenInfo(),SjtuLibInfo(),ShowSjmcStatus(),SjtuDekt(),GetJwc(), #SubscribeJwc(), 
    GetSjtuNews(),
    LotteryPlugin(),
    Show2cyPIC(), #ShowSePIC(),
    GetCanvas(), CanvasiCalBind(), CanvasiCalUnbind(),
    ShowEE0502Comments(),
    GetSjmcLive(), GetFduMcLive(),
    GetMddStatus(),#SubscribeMdd(),
    SjtuHesuan(),
    RandomNum(), ThreeKingdomsRandom(), TarotRandom()
]
GroupPokeList:List[PokeStandardPlugin] = [
    AutoRepoke(), # 自动回复拍一拍
]
helper.updatePluginList(GroupPluginList, PrivatePluginList)

app = Flask(__name__)
class NoticeType(IntEnum):
    NoProcessRequired = 0
    GroupMessageNoProcessRequired = 1
    GroupMessage = 11
    GroupPoke = 12
    GroupRecall = 13
    GroupUpload = 14
    PrivateMessage = 21
    PrivatePoke = 22
    PrivateRecall = 23
    AddGroup = 31
    AddPrivate = 32

def eventClassify(json_data: dict)->NoticeType: 
    """事件分类"""
    if json_data['post_type'] == 'message' and json_data['message_type'] == 'group':
        if json_data['group_id'] in APPLY_GROUP_ID:
            return NoticeType.GroupMessage
        else:
            return NoticeType.GroupMessageNoProcessRequired
    if json_data['post_type'] == 'message' and json_data['message_type'] == 'private':
        return NoticeType.PrivateMessage
    if json_data['post_type'] == 'notice' and json_data['notice_type'] == 'notify' and json_data['sub_type'] == "poke":
        if 'group_id' in json_data.keys() and json_data['group_id'] in APPLY_GROUP_ID:
            return NoticeType.GroupPoke
    if json_data['post_type'] == 'notice' and json_data['notice_type'] == 'group_recall':
        return NoticeType.GroupRecall
    if json_data['post_type'] == 'notice' and json_data['notice_type'] == 'group_upload':
        return NoticeType.GroupUpload
    if json_data['post_type'] == 'request' and json_data['request_type'] == 'friend':
        return NoticeType.AddPrivate
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

    # 私聊消息处理
    elif flag==NoticeType.PrivateMessage:
        msg=data['message'].strip()
        for event in PrivatePluginList:
            if event.judgeTrigger(msg, data):
                if event.executeEvent(msg, data)!=None:
                    break
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
    return "OK"
def initialize():
    createGlobalConfig()
    createFaqDb()
    createBilibiliTable()
    for group in get_group_list():
        groupId = group['group_id']
        createFaqTable(str(groupId))
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
if __name__ == '__main__':
    initialize()
    app.run(host="127.0.0.1", port=5986)