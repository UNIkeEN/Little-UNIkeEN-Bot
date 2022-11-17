import os
import traceback
from flask import Flask, request
from enum import IntEnum

from utils.basicEvent import send
from utils.basicConfigs import *
from utils.standardPlugin import StandardPlugin, PluginGroupManager

from plugins.faq_v2 import MaintainFAQ, AskFAQ, HelpFAQ, createFaqDb, createFaqTable
from plugins.greetings import *
from plugins.checkCoins import *
from plugins.superEmoji import *
from plugins.news import *
from plugins.signIn import *
from plugins.stocks import *
from plugins.jile import *
from plugins.sjtuInfo import *
from plugins.sjmcStatus import *
from plugins.genshin import *
from plugins.roulette import *
# from plugins.lottery import *
from plugins.show2cyPic import *
from plugins.help import *
from plugins.chatWithNLP import *
from plugins.chatWithAnswerbook import *
from plugins.getDekt import DektGroup, GetDektNewActivity
from plugins.getJwc import JwcGroup, GetJwc
from plugins.canvasSync import *
from plugins.getPermission import GetPermission, AddPermission, DelPermission, ShowPermission
from plugins.goBang import GoBangPlugin
from plugins.messageRecorder import GroupMessageRecorder
from plugins.fileRecorder import GroupFileRecorder
from plugins.dropOut import *
from plugins.sjmcLive import SjmcLiveStatus, FduMcLiveStatus
from plugins.sjtuHesuan import SjtuHesuan
from plugins.EE0502 import *

ROOT_PATH = os.path.dirname(os.path.realpath(__file__))
RESOURCES_PATH = os.path.join(ROOT_PATH, "resources")

# 特殊插件需要复用的放在这里
helper = ShowHelp() # 帮助插件
groupMessageRecorder = GroupMessageRecorder() # 群聊消息记录插件


GroupPluginList:List[StandardPlugin]=[ # 指定群启用插件
    groupMessageRecorder,
    helper,ShowStatus(),ServerMonitor(), # 帮助
    GetPermission(), 
    PluginGroupManager([AddPermission(), DelPermission(), ShowPermission()], 'permission'), # 权限
    PluginGroupManager([AskFAQ(), MaintainFAQ(), HelpFAQ()],'faq'), # 问答库与维护
    PluginGroupManager([MorningGreet(), NightGreet()], 'greeting'), # 早安晚安
    PluginGroupManager([CheckCoins(), AddAssignedCoins(),CheckTransactions()],'money'), # 查询金币,查询记录,增加金币（管理员）
    PluginGroupManager([FireworksFace(), FirecrackersFace(), BasketballFace(), HotFace()], 'superemoji'), # 超级表情
    PluginGroupManager([ShowNews()],'news'),  # 新闻
    PluginGroupManager([SignIn()], 'signin'),  # 签到
    PluginGroupManager([QueryStocksHelper(), QueryStocks(), BuyStocksHelper(), BuyStocks(), QueryStocksPriceHelper(), QueryStocksPrice()],'stocks'), # 股票
    PluginGroupManager([Chai_Jile(), Yuan_Jile()],'jile'), # 柴/元神寄了
    PluginGroupManager([SjtuCanteenInfo(),SjtuLibInfo(), SjtuHesuan()],'sjtuinfo'),
    PluginGroupManager([ShowSjmcStatus(),SjmcLiveStatus(),FduMcLiveStatus()], 'sjmc'), #MC社服务
    DektGroup(),JwcGroup(), # 校园服务,dekt服务,jwc服务
    PluginGroupManager([GenshinCookieBind(), GenshinDailyNote()],'genshin'), # 原神绑定与实时便笺
    PluginGroupManager([RoulettePlugin()],'roulette'), # 轮盘赌
    # LotteryPlugin(), # 彩票 TODO
    PluginGroupManager([GoBangPlugin()],'gobang'),
    PluginGroupManager([Show2cyPIC()], 'anime'), #ShowSePIC(), # 来点图图，来点涩涩(关闭)
    PluginGroupManager([ChatWithAnswerbook(), ChatWithNLP()], 'chat'), # 答案之书/NLP
    PluginGroupManager([GetCanvas(), CanvasiCalBind(), CanvasiCalUnbind()], 'canvas'), # 日历馈送
    PluginGroupManager([DropOut()], 'dropout'), # 一键退学
    PluginGroupManager([ShowEE0502Comments()], 'izf'), # 张峰
]
PrivatePluginList:List[StandardPlugin]=[ # 私聊启用插件
    helper, 
    ShowStatus(),ServerMonitor(),
    CheckCoins(),AddAssignedCoins(),CheckTransactions(),
    ShowNews(),
    MorningGreet(), NightGreet(),
    SignIn(),
    QueryStocksHelper(), QueryStocks(), BuyStocksHelper(), BuyStocks(), QueryStocksPriceHelper(), QueryStocksPrice(),
    SjtuCanteenInfo(),SjtuLibInfo(),ShowSjmcStatus(),GetDektNewActivity(),GetJwc(),
    GenshinCookieBind(), GenshinDailyNote(),
    # LotteryPlugin(),
    Show2cyPIC(), #ShowSePIC(),
    GetCanvas(), CanvasiCalBind(), CanvasiCalUnbind(),
    ShowEE0502Comments(),
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
            event: StandardPlugin
            if event.judgeTrigger(msg, data):
                ret = event.executeEvent(msg, data)
                if ret != None:
                    return ret
    elif flag == NoticeType.GroupUpload:
        for event in [GroupFileRecorder()]:
            event.uploadFile(data)
    # 群内拍一拍回拍
    elif flag==NoticeType.GroupPoke: 
        if data['target_id'] == data['self_id']:
            send(data['group_id'], f"[CQ:poke,qq={data['sender_id']}]")
            
    # 自动加好友
    elif flag==NoticeType.AddPrivate:
        set_friend_add_request(data['flag'], True)
    return "OK"
def initialize():
    if not os.path.isdir('./data/tmp'):
        os.makedirs('./data/tmp')
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