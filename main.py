import os
import traceback
from flask import Flask, request
from enum import IntEnum

from utils.basicEvent import send
from utils.basicConfigs import *
from utils.standardPlugin import StandardPlugin, PluginGroupManager, EmptyPlugin

from plugins.faq_v2 import MaintainFAQ, AskFAQ, HelpFAQ, createFaqDb, createFaqTable
from plugins.greetings import MorningGreet, NightGreet
from plugins.checkCoins import CheckCoins, AddAssignedCoins, CheckTransactions
from plugins.superEmoji import FirecrackersFace, FireworksFace, BasketballFace, HotFace
from plugins.news import ShowNews
from plugins.signIn import SignIn
from plugins.stocks import *
from plugins.sjtuInfo import SjtuCanteenInfo, SjtuLibInfo
from plugins.sjmcStatus_v2 import ShowSjmcStatus
from plugins.genshin import GenshinCookieBind, GenshinDailyNote
from plugins.roulette import RoulettePlugin
from plugins.lottery import LotteryPlugin
from plugins.show2cyPic import Show2cyPIC, ShowSePIC
from plugins.help_v2 import ShowHelp, ShowStatus, ServerMonitor
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

# ???????????????????????????????????????
helper = ShowHelp() # ????????????
groupMessageRecorder = GroupMessageRecorder() # ????????????????????????


GroupPluginList:List[StandardPlugin]=[ # ?????????????????????
    groupMessageRecorder,
    helper,ShowStatus(),ServerMonitor(), # ??????
    GetPermission(), 
    PluginGroupManager([AddPermission(), DelPermission(), ShowPermission(), AddGroupAdminToBotAdmin()], 'permission'), # ??????
    PluginGroupManager([AskFAQ(), MaintainFAQ(), HelpFAQ()],'faq'), # ??????????????????
    PluginGroupManager([MorningGreet(), NightGreet()], 'greeting'), # ????????????
    PluginGroupManager([CheckCoins(), AddAssignedCoins(),CheckTransactions()],'money'), # ????????????,????????????,???????????????????????????
    PluginGroupManager([FireworksFace(), FirecrackersFace(), BasketballFace(), HotFace()], 'superemoji'), # ????????????
    PluginGroupManager([ShowNews()],'news'),  # ??????
    PluginGroupManager([SignIn()], 'signin'),  # ??????
    PluginGroupManager([QueryStocksHelper(), QueryStocks(), BuyStocksHelper(), BuyStocks(), QueryStocksPriceHelper(), QueryStocksPrice()],'stocks'), # ??????
    PluginGroupManager([Chai_Jile(), Yuan_Jile()],'jile'), # ???/????????????
    PluginGroupManager([SjtuCanteenInfo(),SjtuLibInfo(), SjtuHesuan(), GetMddStatus(), #SubscribeMdd(), # ????????????, ?????????, ?????????, ?????????
                        PluginGroupManager([MonitorMddStatus()], 'mddmonitor'),],'sjtuinfo'), 
    PluginGroupManager([ShowSjmcStatus(), GetSjmcLive(), GetFduMcLive(),
                        PluginGroupManager([SjmcLiveMonitor(),FduMcLiveMonitor()], 'mclive')], 'sjmc'), #MC?????????
    PluginGroupManager([GetJwc(), #SubscribeJwc() ,
                        SjtuJwcMonitor(), GetSjtuNews(), SjtuDekt(),# jwc??????, jwc??????, ????????????, ????????????
                        PluginGroupManager([SjtuDektMonitor()], 'dekt')], 'jwc'), 
    PluginGroupManager([GenshinCookieBind(), GenshinDailyNote()],'genshin'), # ???????????????????????????
    PluginGroupManager([RoulettePlugin()],'roulette'), # ?????????
    PluginGroupManager([LotteryPlugin()],'lottery'), # ?????? TODO
    # PluginGroupManager([GoBangPlugin()],'gobang'),
    PluginGroupManager([Show2cyPIC()], 'anime'), #ShowSePIC(), # ???????????????????????????(??????)
    PluginGroupManager([ChatWithAnswerbook(), ChatWithNLP()], 'chat'), # ????????????/NLP
    PluginGroupManager([GetCanvas(), CanvasiCalBind(), CanvasiCalUnbind()], 'canvas'), # ????????????
    # PluginGroupManager([DropOut()], 'dropout'), # ????????????
    PluginGroupManager([ShowEE0502Comments()], 'izf'), # ??????
    PluginGroupManager([ActReportPlugin()], 'actreport'), #????????????
]
PrivatePluginList:List[StandardPlugin]=[ # ??????????????????
    helper, 
    ShowStatus(),ServerMonitor(),
    CheckCoins(),AddAssignedCoins(),CheckTransactions(),
    ShowNews(),
    MorningGreet(), NightGreet(),
    SignIn(),
    QueryStocksHelper(), QueryStocks(), BuyStocksHelper(), BuyStocks(), QueryStocksPriceHelper(), QueryStocksPrice(),
    SjtuCanteenInfo(),SjtuLibInfo(),ShowSjmcStatus(),SjtuDekt(),GetJwc(), #SubscribeJwc(), 
    GetSjtuNews(),
    GenshinCookieBind(), GenshinDailyNote(),
    LotteryPlugin(),
    Show2cyPIC(), #ShowSePIC(),
    GetCanvas(), CanvasiCalBind(), CanvasiCalUnbind(),
    ShowEE0502Comments(),
    GetSjmcLive(), GetFduMcLive(),
    GetMddStatus(),#SubscribeMdd(),
    SjtuHesuan(),
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
    """????????????"""
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
    # ??????????????????
    data = request.get_json()
    # ???????????????????????????
    flag=eventClassify(data)
    # ???????????????
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

    # ??????????????????
    elif flag==NoticeType.PrivateMessage:
        msg=data['message'].strip()
        for event in PrivatePluginList:
            event: StandardPlugin
            if event.judgeTrigger(msg, data):
                ret = event.executeEvent(msg, data)
                if ret != None:
                    return ret
    elif flag == NoticeType.GroupUpload:
        for event in [GroupFileRecorder()]:
            event.uploadFile(data)
    # ?????????????????????
    elif flag==NoticeType.GroupPoke: 
        if data['target_id'] == data['self_id']:
            send(data['group_id'], f"[CQ:poke,qq={data['sender_id']}]")
            
    # ???????????????
    elif flag==NoticeType.AddPrivate:
        set_friend_add_request(data['flag'], True)
    return "OK"
def initialize():
    createGlobalConfig()
    createFaqDb()
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