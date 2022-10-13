import re
from typing import Tuple, Union, Any
from threading import Timer
from utils.basicEvent import *
from utils.basicConfigs import *
from utils.standardPlugin import StandardPlugin
from utils.accountOperation import get_user_coins, update_user_coins
from utils.goBangGame import NCOLS, NROWS, GoBangGame, drawGoBangPIC
from enum import IntEnum
import traceback
GOBANG_SPEND_COINS = 0
CMD_GOBANG = ['开始五子棋','取消五子棋','接受五子棋','认输']
CMD_GOBANG_ONGOING = lambda txt: re.match('^([1-9]|0[1-9]|1[0-%d])([A-%s])$'%(NROWS%10,"_ABCDEFGHIJKLMNOPQRSTUVWXYZ"[NCOLS]), txt) != None
class GameStatus(IntEnum):
    FREE = 0
    READY = 1
    GAMING = 2
class GoBangGroupInterface():
    """五子棋群聊接口类"""
    def __init__(self, group_id):
        self.player=[0, 0]
        self.status=GameStatus.FREE
        self.group_id=group_id # 群号（用于读取金币数量）
        self.round_index=0 # 在0和1之间切换，对应当前开枪者
        self.game = GoBangGame()
        self.timer= None
    def refresh(self):
        self.player=[0, 0]
        self.status=GameStatus.FREE
        self.round_index=0 # 在0和1之间切换，对应当前开枪者
        self.timer = None
        self.game.refresh()
    def get_cmd(self, msg:str, data)->Union[None, str]:
        userId = data['user_id']
        groupId = data['group_id']
        # init阶段，发起决斗申请
        if self.status == GameStatus.FREE:
            if startswith_in(msg, ['开始五子棋']):
                if get_user_coins(userId) < GOBANG_SPEND_COINS:
                    return '金币不足，五子棋需%d金币'%GOBANG_SPEND_COINS
                self.status = GameStatus.READY
                self.player[0] = userId
                self.timer = Timer(45, self.prepare_timeout)
                self.timer.start()
                return "[CQ:at,qq=%d]向群友发起五子棋挑战，回复“接受五子棋”迎接挑战吧！"%userId
        elif self.status == GameStatus.READY:
            if msg == '接受五子棋':
                if userId == self.player[0]:
                    return '自己不能和自己下棋'
                if get_user_coins(userId) < GOBANG_SPEND_COINS:
                    return '金币不足，五子棋需%d金币'%GOBANG_SPEND_COINS
                self.timer.cancel()
                self.status = GameStatus.GAMING
                self.player[1] = userId
                self.round_index = 0
                picPath = drawGoBangPIC([], [], groupId)
                picPath = f'file:///{ROOT_PATH}/'+picPath
                send(groupId, '开始游戏，由发起挑战者执黑先行！', 'group')
                self.timer = Timer(60, self.ongoing_timeout)
                self.timer.start()
                return f'[CQ:image,file={picPath}]'
        elif self.status == GameStatus.GAMING:
            if userId != self.player[self.round_index]:
                return None
            if msg == '认输':
                winner = self.player[1^self.round_index]
                loser = self.player[self.round_index]
                self.timer.cancel()
                self.refresh()
                return '恭喜[CQ:at,qq=%d]战胜[CQ:at,qq=%d],取得本局五子棋的胜利！'%(winner, loser)
            if CMD_GOBANG_ONGOING(msg):
                x, y = re.findall('^([1-9]|0[1-9]|1[0-%d])([A-%s])$'%(NROWS%10,"_ABCDEFGHIJKLMNOPQRSTUVWXYZ"[NCOLS]), msg)[0]
                x = int(x) - 1
                y = ord(y) - ord('A')
                valid = self.game.act((x, y))
                if not valid:
                    return "此处不能落子"
                self.timer.cancel()
                done = self.game.done()
                if done:
                    winner = self.player[self.round_index]
                    loser = self.player[1^self.round_index]
                    self.refresh()
                    return '五子连珠！恭喜[CQ:at,qq=%d]战胜[CQ:at,qq=%d],取得本局五子棋的胜利！'%(winner, loser)
                self.round_index ^= 1
                black, white = self.game.getPieceLocs()
                picPath = drawGoBangPIC(black, white, groupId)
                picPath = f'file:///{ROOT_PATH}/'+picPath
                self.timer = Timer(60, self.ongoing_timeout)
                self.timer.start()
                return f'[CQ:image,file={picPath}]'
        else:
            warning("unexpected gobang status")
            return None
    def prepare_timeout(self): # 准备阶段超时无人应答
        self.timer.cancel()
        send(self.group_id,'⏰45s内无应答，[CQ:at,qq=%d]的决斗请求已自动取消'%(self.player[0]))
        self.refresh()
    def ongoing_timeout(self): # 游戏阶段超时无人应答
        self.timer.cancel()
        send(self.group_id,'⏰60s内无应答，决斗已自动结算，胜利者为[CQ:at,qq=%d]'%(self.player[1^self.round_index]))
        self.refresh()
class GoBangPlugin(StandardPlugin):
    def __init__(self) -> None:
        self.goBangDict = {}
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return startswith_in(msg, CMD_GOBANG) or CMD_GOBANG_ONGOING(msg)
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        groupId = data['group_id']
        userId = data['user_id']
        if groupId not in self.goBangDict.keys():
            self.goBangDict[groupId] = GoBangGroupInterface(groupId)
        try:
            ret = self.goBangDict[groupId].get_cmd(msg, data)
            if isinstance(ret, str):
                send(groupId, ret)
        except Exception as e:
            warning("exception in gobang: {}, {}".format(e, traceback.format_exc()))

        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'GoBang',
            'description': '五子棋',
            'commandDescription': '开始五子棋/接受五子棋/认输/A1、B2...',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }