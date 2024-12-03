import re
import os, os.path
from dataclasses import dataclass
from io import BytesIO
from typing import Dict, Iterable, List, NoReturn, Union, Any, Optional

from utils.basicEvent import send, warning
from utils.basicConfigs import sqlConfig, ROOT_PATH, SAVE_TMP_PATH
from utils.standardPlugin import StandardPlugin
from utils.basicConfigs import BOT_SELF_QQ
from .board import MoveResult
from .config import Config
from .engine import EngineError
from .game import AiPlayer, Game, Player
from .move import Move
from .chessdb import drawChessdb
from PIL import Image

class ChineseChessHelper(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any)->bool:
        return msg in ['象棋帮助']
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        send(target, (
            '象棋帮助：象棋帮助\n'
            '执红发起游戏：象棋, -lxq\n'
            '执黑发起游戏：执黑下象棋\n'
            '接受游戏：应战\n'
            '认输：   认输\n'
            '下棋： 炮二平五/h2e2/...\n'
            '显示棋谱招法： 谱招\n'
            '邀请电脑下棋： 添加电脑\n'
            '难度设置： 难度设置 8\n'
            '悔棋： 悔棋'
        ), data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'ChineseChessHelper',
            'description': '中国象棋帮助',
            'commandDescription': '象棋帮助',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }

class ChineseChessPlugin(StandardPlugin):
    def __init__(self, 
                 engineType:str='uci',
                 enginePath:Optional[str]=None, 
                 engineOptions:Dict[str, str]={}):
        self.startCommands = ['下象棋', '-lxq', '执黑下象棋']
        self.acceptCommands = ['应战']
        self.defeatCommands = ['认输', '掀棋盘', '不下了', '结束对局']
        self.ckptCommands = ['保存对局']
        self.chessdbCommands = ['谱招', '谱着']
        self.addComputerCommands = ['添加电脑', '加入电脑']
        self.games:Dict[int, Game] = {}
        # self.timers: Dict[int, ] = {}
        self.matchMovePattern = re.compile(r"^\S\S[a-iA-I平进退上下][0-9一二三四五六七八九]$")
        self.difficultyPattern = re.compile(r'^难度设置\s*(\d)')
        self.enginePath = enginePath
        self.engineOptions = engineOptions
        self.level = {}
        self.engineType = engineType
        
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return (msg in self.startCommands or 
            msg in self.acceptCommands or 
            msg in self.defeatCommands or
            msg in self.ckptCommands or
            self.match_move(msg) or
            msg in self.chessdbCommands or
            msg in self.addComputerCommands or
            self.match_difficulty(msg))
        
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        group_id = data['group_id']
        user_id = data['user_id']
        if msg in self.startCommands:
            if self.game_running(data):
                send(target, '[CQ:reply,id={}]群内有正在进行的战斗，战斗结束才能发起挑战'.format(data['message_id']), data['message_type'])
            else:
                game = Game()
                player = self.new_player(data)
                if msg in ['下象棋', '-lxq']:
                    game.player_red = player
                    send(target, '群友 {} 执红，向大家发起中国象棋挑战，输入“应战”接受挑战吧！'.format(player), data['message_type'])
                else:
                    game.player_black = player
                    send(target, '群友 {} 执黑，向大家发起中国象棋挑战，输入“应战”接受挑战吧！'.format(player), data['message_type'])
                self.games[target] = game
        elif msg in self.ckptCommands:
            game = self.games.get(group_id, None)
            if game == None:
                send(target, '[CQ:reply,id={}]尚未有人发起战斗，请输入 下象棋、-lxq、执黑下象棋 发起挑战'.format(data['message_id']), data['message_type'])
            elif len(game.history) <= 1:
                send(target, '[CQ:reply,id={}]对局尚未开始'.format(data['message_id']), data['message_type'])
            else:
                fen = game.fen()
                send(target, fen, data['message_type'])
        elif msg in self.acceptCommands:
            game = self.games.get(group_id, None)
            if game == None:
                send(target, '[CQ:reply,id={}]尚未有人发起战斗，请输入 下象棋、-lxq、执黑下象棋 发起挑战'.format(data['message_id']), data['message_type'])
            elif game.player_red != None and game.player_black != None:
                send(target, '[CQ:reply,id={}]对局正在进行中，请耐心等待'.format(data['message_id']), data['message_type'])
            elif (game.player_red == None) ^ (game.player_black == None):
                player = self.new_player(data)
                if game.player_red == None:
                    if game.player_black.id == player.id:
                        send(target, '[CQ:reply,id={}]自己不能和自己下棋'.format(data['message_id']), data['message_type'])
                    else:
                        game.player_red = player
                        imgPath = self.draw_board(game, group_id)
                        send(target, f'[CQ:image,file=file:///{imgPath}]对局开始，请执红者 {game.player_red} 先行', data['message_type'])
                else:
                    if game.player_red.id == player.id:
                        send(target, '[CQ:reply,id={}]自己不能和自己下棋'.format(data['message_id']), data['message_type'])
                    else:
                        game.player_black = player
                        imgPath = self.draw_board(game, group_id)
                        send(target, f'[CQ:image,file=file:///{imgPath}]对局开始，请执红者 {game.player_red} 先行', data['message_type'])
            else: 
                send(target, '[CQ:reply,id={}]内部错误 game.player_red == None and game.player_black == None'.format(data['message_id']), data['message_type'])
                warning("象棋 game.player_red == None and game.player_black == None in group %d"%(target))
        elif msg in self.defeatCommands:
            game = self.games.get(group_id, None)
            if game == None:
                send(target, '[CQ:reply,id={}]群内没有对局，请先发起对局'.format(data['message_id']), data['message_type'])
            elif (game.player_red == None) ^ (game.player_black == None):
                if game.player_red != None and game.player_red.id == user_id:
                    send(target, '没有成员应战，对局结束', data['message_type'])
                    self.stop_game(group_id)
                elif game.player_black != None and game.player_black.id == user_id:
                    send(target, '没有成员应战，对局结束', data['message_type'])
                    self.stop_game(group_id)
                else:
                    send(target, '[CQ:reply,id={}]请先应战'.format(data['message_id']), data['message_type'])
            elif game.player_red != None and game.player_black != None:
                if game.player_red.id == user_id:
                    send(target, '红方认输，恭喜 {} 获胜！'.format(game.player_black), data['message_type'])
                    self.stop_game(group_id)
                elif game.player_black.id == user_id:
                    send(target, '黑方认输，恭喜 {} 获胜！'.format(game.player_red), data['message_type'])
                    self.stop_game(group_id)
                else:
                    send(target, '[CQ:reply,id={}]对局正在进行中，请耐心等待'.format(data['message_id']), data['message_type'])
            else:
                send(target, '[CQ:reply,id={}]内部错误 game.player_red == None and game.player_black == None'.format(data['message_id']), data['message_type'])
                warning("象棋 game.player_red == None and game.player_black == None in group %d"%(target))
        elif self.match_move(msg):
            game = self.games.get(group_id, None)
            if game == None:
                if self.get_move(msg, game) != None:
                    send(target, '[CQ:reply,id={}]群内没有对局，请先发起对局'.format(data['message_id']), data['message_type'])
            elif game.player_black == None or game.player_red == None:
                if self.get_move(msg, game) != None:
                    send(target, '[CQ:reply,id={}]游戏尚未开始，请先回复“应战”接受对局'.format(data['message_id']), data['message_type'])
            elif game.player_next != None and game.player_next.id != user_id:
                if self.get_move(msg, game) != None:
                    send(target, '[CQ:reply,id={}]不是你的回合'.format(data['message_id']), data['message_type'])
            else:
                move = self.get_move(msg, game)
                if move == None:
                    send(target, "[CQ:reply,id={}]请发送正确的走法，如 “炮二平五” 或 “h2e2”".format(data['message_id']), data['message_type'])
                else:
                    result = game.push(move)
                    if result == MoveResult.ILLEAGAL:
                        send(target, "[CQ:reply,id={}]不正确的走法，请重新输入".format(data['message_id']), data['message_type'])
                    elif result == MoveResult.CHECKED:
                        send(target, "不能送将，请改变招法".format(data['message_id']), data['message_type'])
                    elif result == MoveResult.RED_WIN:
                        imgPath = self.draw_board(game, group_id)
                        send(target, f'[CQ:image,file=file:///{imgPath}]黑方被将死，恭喜 {game.player_red} 获胜！', data['message_type'])
                        self.stop_game(group_id)
                    elif result == MoveResult.BLACK_WIN:
                        imgPath = self.draw_board(game, group_id)
                        send(target, f'[CQ:image,file=file:///{imgPath}]红方被将死，恭喜 {game.player_black} 获胜！', data['message_type'])
                        self.stop_game(group_id)
                    elif result == MoveResult.DRAW:
                        send(target, "根据规则，局面判和", data['message_type'])
                        self.stop_game(group_id)
                    else:
                        if isinstance(game.player_next, AiPlayer):
                            if game.player_next.time > 40000:
                                send(target, f'小马正在思考....', data['message_type'])
                            move = game.player_next.get_move(game.position())
                            result = game.push(move)
                            imgPath = self.draw_board(game, group_id)
                            if result == None:
                                send(target, f'[CQ:image,file=file:///{imgPath}]下一手轮到 {game.player_next} 行棋', data['message_type'])
                            elif result == MoveResult.CHECKED:
                                send(target, f'[CQ:image,file=file:///{imgPath}]电脑认输，恭喜 {game.player_next} 获胜！', data['message_type'])
                                self.stop_game(group_id)
                            elif result == MoveResult.RED_WIN or result == MoveResult.BLACK_WIN:
                                send(target, f'[CQ:image,file=file:///{imgPath}]可惜，下一把再继续努力吧', data['message_type'])
                            elif result == MoveResult.DRAW:
                                send(target, "根据规则，局面判和", data['message_type'])
                                self.stop_game(group_id)
                        else:
                            imgPath = self.draw_board(game, group_id)
                            send(target, f'[CQ:image,file=file:///{imgPath}]下一手轮到 {game.player_next} 行棋', data['message_type'])
        elif self.match_difficulty(msg):
            difficulty = int(self.difficultyPattern.findall(msg)[0])
            if difficulty < 1 or difficulty > 9:
                send(target, "[CQ:reply,id={}]难度需要为1-9之间的整数".format(data['message_id']), data['message_type'])
            else:
                send(target, "[CQ:reply,id={}]设置成功，当前难度{}".format(data['message_id'],difficulty), data['message_type'])
                self.level[group_id] = difficulty
        elif msg in self.chessdbCommands:
            game = self.games.get(group_id, None)
            if game == None:
                send(target, '[CQ:reply,id={}]群内没有对局，请先发起对局'.format(data['message_id']), data['message_type'])
            # elif len(game.history) <= 1:
            #     send(target, '[CQ:reply,id={}]对局尚未开始'.format(data['message_id']), data['message_type'])
            else:
                imgPath = self.draw_chessdb(game, group_id)
                if imgPath != None:
                    send(target, f'[CQ:image,file=file:///{imgPath}]', data['message_type'])
                else:
                    send(target, f"[CQ:reply,id={data['message_id']}]查询失败", data['message_type'])
        elif msg in self.addComputerCommands:
            game = self.games.get(group_id, None)
            if game == None:
                send(target, '[CQ:reply,id={}]群内没有对局，请先发起对局'.format(data['message_id']), data['message_type'])
            elif (game.player_red == None) ^ (game.player_black == None):
                level = self.level.get(group_id, 8)
                ai_player = self.new_ai_player(level)
                if ai_player == None:
                    send(target, f'AI创建失败', data['message_type'])
                else:
                    if game.player_red == None:
                        game.player_red = ai_player
                        move = ai_player.get_move(game.position())
                        game.push(move)
                        imgPath = self.draw_board(game, group_id)
                        send(target, f'电脑下出了{move.chinese()}[CQ:image,file=file:///{imgPath}]下一手轮到 {game.player_next} 行棋', data['message_type'])
                    else:
                        game.player_black = ai_player
                        imgPath = self.draw_board(game, group_id)
                        send(target, f'[CQ:image,file=file:///{imgPath}]对局开始，请执红者 {game.player_red} 先行', data['message_type'])
            else:
                send(target, '[CQ:reply,id={}]双方都已落座，电脑加不进来了QAQ'.format(data['message_id']), data['message_type'])
        return 'OK'
    
    def match_move(self, msg:str)->bool:
        return self.matchMovePattern.match(msg) != None
    
    def match_difficulty(self, msg: str)->bool:
        return self.difficultyPattern.match(msg) != None
    
    def get_move(self, msg, game):
        try:
            move = Move.from_ucci(msg)
            return move
        except ValueError:
            try:
                move = Move.from_chinese(game, msg)
                return move
            except ValueError:
                return None
            
    def getPluginInfo(self, )->Any:
        return {
            'name': 'ChineseChessPlugin',
            'description': '中国象棋',
            'commandDescription': '下象棋/-lxq',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }

    def game_running(self, data:Any) -> bool:
        group_id = data['group_id']
        return self.games.get(group_id, None) != None

    def new_player(self, data:Any) -> Player:
        if 'card' not in data['sender'].keys():
            card = data['anonymous']['name']
        else:
            card = data['sender']['card']
        if card == '':
            card = data['sender']['nickname']
        return Player(data['user_id'], card)
    
    def new_ai_player(self, level:int) -> Optional[AiPlayer]:
        try:
            return AiPlayer(BOT_SELF_QQ, self.engineType, level, self.enginePath, self.engineOptions)
        except EngineError as e:
            warning(str(e))
            return None

    def stop_game(self, group_id: int) -> Optional[Game]:
        game = self.games.pop(group_id, None)
        if game != None:
            game.close_engine()
        return game
    
    def draw_board(self, game: Game, group_id: int)->str:
        imgPath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'cchess_%d.png'%(group_id))
        Image.open(game.draw()).save(imgPath)
        return imgPath
    
    def draw_chessdb(self, game: Game, group_id: int)->Optional[str]:
        imgPath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'chessdb_%d.png'%(group_id))
        result = drawChessdb(game, imgPath)
        if result:
            return imgPath
        else:
            return None
