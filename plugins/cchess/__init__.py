import re
import os, os.path
from dataclasses import dataclass
from io import BytesIO
from typing import Dict, Iterable, List, NoReturn, Union, Any, Optional

from utils.basicEvent import send, warning
from utils.basicConfigs import sqlConfig, ROOT_PATH, SAVE_TMP_PATH
from utils.standardPlugin import StandardPlugin
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
    def __init__(self):
        self.startCommands = ['下象棋', '-lxq', '执黑下象棋']
        self.acceptCommands = ['应战']
        self.defeatCommands = ['认输', '掀棋盘', '不下了', '结束对局']
        self.ckptCommands = ['保存对局']
        self.chessdbCommands = ['谱招', '谱着']
        self.games:Dict[str, Game] = {}
        # self.timers: Dict[str, ] = {}
        self.matchMovePattern = re.compile(r"^\S\S[a-iA-I平进退上下][0-9一二三四五六七八九]$")
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return (msg in self.startCommands or 
            msg in self.acceptCommands or 
            msg in self.defeatCommands or
            msg in self.ckptCommands or
            self.match_move(msg) or
            msg in self.chessdbCommands)
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
                    send(target, '群友 {} 执红，向大家发起象棋挑战，输入“应战”接受挑战吧！'.format(player), data['message_type'])
                else:
                    game.player_black = player
                    send(target, '群友 {} 执黑，向大家发起象棋挑战，输入“应战”接受挑战吧！'.format(player), data['message_type'])
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
                        imgPath = self.draw_board(game, data)
                        send(target, f'[CQ:image,file=files:///{imgPath}]对局开始，请执红者 [CQ:at,qq={game.player_red.id}] 先行', data['message_type'])
                else:
                    if game.player_red.id == player.id:
                        send(target, '[CQ:reply,id={}]自己不能和自己下棋'.format(data['message_id']), data['message_type'])
                    else:
                        game.player_black = player
                        imgPath = self.draw_board(game, data)
                        send(target, f'[CQ:image,file=files:///{imgPath}]对局开始，请执红者 [CQ:at,qq={game.player_red.id}] 先行', data['message_type'])
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
                    self.stop_game(data)
                elif game.player_black != None and game.player_black.id == user_id:
                    send(target, '没有成员应战，对局结束', data['message_type'])
                    self.stop_game(data)
                else:
                    send(target, '[CQ:reply,id={}]请先应战'.format(data['message_id']), data['message_type'])
            elif game.player_red != None and game.player_black != None:
                if game.player_red.id == user_id:
                    send(target, '红方认输，恭喜 {} 获胜！'.format(game.player_black), data['message_type'])
                    self.stop_game(data)
                elif game.player_black.id == user_id:
                    send(target, '黑方认输，恭喜 {} 获胜！'.format(game.player_red), data['message_type'])
                    self.stop_game(data)
                else:
                    send(target, '[CQ:reply,id={}]对局正在进行中，请耐心等待'.format(data['message_id']), data['message_type'])
            else:
                send(target, '[CQ:reply,id={}]内部错误 game.player_red == None and game.player_black == None'.format(data['message_id']), data['message_type'])
                warning("象棋 game.player_red == None and game.player_black == None in group %d"%(target))
        elif self.match_move(msg):
            game = self.games.get(group_id, None)
            if game == None:
                send(target, '[CQ:reply,id={}]群内没有对局，请先发起对局'.format(data['message_id']), data['message_type'])
            elif game.player_black == None or game.player_red == None:
                send(target, '[CQ:reply,id={}]游戏尚未开始，请先回复“应战”接受对局'.format(data['message_id']), data['message_type'])
            elif game.player_next != None and game.player_next.id != user_id:
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
                        imgPath = self.draw_board(game, data)
                        send(target, f'[CQ:image,file=files:///{imgPath}]黑方被将死，恭喜 {game.player_red} 获胜！', data['message_type'])
                        self.stop_game(data)
                    elif result == MoveResult.BLACK_WIN:
                        imgPath = self.draw_board(game, data)
                        send(target, f'[CQ:image,file=files:///{imgPath}]红方被将死，恭喜 {game.player_black} 获胜！', data['message_type'])
                        self.stop_game(data)
                    elif result == MoveResult.DRAW:
                        send(target, "根据规则，局面判和", data['message_type'])
                        self.stop_game(data)
                    else:
                        imgPath = self.draw_board(game, data)
                        send(target, f'[CQ:image,file=files:///{imgPath}]下一手轮到 {game.player_next} 行棋', data['message_type'])
        elif msg in self.chessdbCommands:
            game = self.games.get(group_id, None)
            if game == None:
                send(target, '[CQ:reply,id={}]群内没有对局，请先发起对局'.format(data['message_id']), data['message_type'])
            # elif len(game.history) <= 1:
            #     send(target, '[CQ:reply,id={}]对局尚未开始'.format(data['message_id']), data['message_type'])
            else:
                imgPath = self.draw_chessdb(game, data)
                if imgPath != None:
                    send(target, f'[CQ:image,file=files:///{imgPath}]', data['message_type'])
                else:
                    send(target, f"[CQ:reply,id={data['message_id']}]查询失败", data['message_type'])
                
    def match_move(self, msg:str)->bool:
        return self.matchMovePattern.match(msg) != None
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

    def stop_game(self, data:Any) -> Optional[Game]:
        return self.games.pop(data['group_id'], None)

    def draw_board(self, game, data)->str:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        imgPath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'cchess_%d.png'%(data['group_id']))
        Image.open(game.draw()).save(imgPath)
        return imgPath
    def draw_chessdb(self, game, data)->Optional[str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        imgPath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'chessdb_%d.png'%(data['group_id']))
        result = drawChessdb(game, imgPath)
        if result:
            return imgPath
        else:
            return None
# @dataclass
# class Options:
#     stop: bool = False
#     show: bool = False
#     repent: bool = False
#     battle: bool = False
#     reload: bool = False
#     black: bool = False
#     level: int = 4
#     move: str = ""


# async def new_player(event: Union[V11MEvent, V12MEvent]) -> Player:
#     user_id = event.get_user_id()
#     user_name = ""
#     if isinstance(event, V11MEvent):
#         user_name = event.sender.card or event.sender.nickname or ""
#     else:
#         assert isinstance(bot, V12Bot)
#         resp = await bot.get_user_info(user_id=user_id)
#         user_name = resp["user_displayname"] or resp["user_name"]
#     return Player(user_id, user_name)

# async def send(msgs: Union[str, Iterable[Union[str, BytesIO]]] = "") -> NoReturn:
#     if not msgs:
#         await matcher.finish()
#     if isinstance(msgs, str):
#         await matcher.finish(msgs)

#     if isinstance(bot, V11Bot):
#         message = V11Msg()
#         for msg in msgs:
#             if isinstance(msg, BytesIO):
#                 message.append(V11MsgSeg.image(msg))
#             else:
#                 message.append(msg)
#     else:
#         message = V12Msg()
#         for msg in msgs:
#             if isinstance(msg, BytesIO):
#                 resp = await bot.upload_file(
#                     type="data", name="cchess", data=msg.getvalue()
#                 )
#                 file_id = resp["file_id"]
#                 message.append(V12MsgSeg.image(file_id))
#             else:
#                 message.append(msg)
#     await matcher.finish(message)

# try:
#     args = parser.parse_args(argv)
# except ParserExit as e:
#     if e.status == 0:
#         await send(__plugin_meta__.usage)
#     await send()

# options = Options(**vars(args))

# cid = get_cid(bot, event)
# if not games.get(cid, None):
#     if options.move:
#         await send()

#     if options.stop or options.show or options.repent:
#         await send("没有正在进行的游戏")

#     if not options.battle and not 1 <= options.level <= 8:
#         await send("等级应在 1~8 之间")

#     if options.reload:
#         try:
#             game = await Game.load_record(cid)
#         except EngineError:
#             await send("象棋引擎加载失败，请检查设置")
#         if not game:
#             await send("没有找到被中断的游戏")
#         games[cid] = game
#         await send(
#             (
#                 (
#                     f"游戏发起时间：{game.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
#                     f"红方：{game.player_red}\n"
#                     f"黑方：{game.player_black}\n"
#                     f"下一手轮到：{game.player_next}\n"
#                 ),
#                 game.draw(),
#             )
#         )

#     game = Game()
#     player = await new_player(event)
#     if options.black:
#         game.player_black = player
#     else:
#         game.player_red = player

#     msg = f"{player} 发起了游戏 象棋！\n发送 中文纵线格式如“炮二平五” 或 起始坐标格式如“h2e2” 下棋"

#     if not options.battle:
#         try:
#             ai_player = AiPlayer(options.level)
#             await ai_player.engine.open()

#             if options.black:
#                 game.player_red = ai_player
#                 move = await ai_player.get_move(game.position())
#                 move_chi = move.chinese(game)
#                 result = game.push(move)
#                 if result:
#                     await send("象棋引擎返回不正确，请检查设置")
#                 msg += f"\n{ai_player} 下出 {move_chi}"
#             else:
#                 game.player_black = ai_player
#         except EngineError:
#             await send("象棋引擎加载失败，请检查设置")

#     games[cid] = game
#     set_timeout(matcher, cid)
#     await game.save_record(cid)
#     await send((msg, game.draw()))

# game = games[cid]
# set_timeout(matcher, cid)
# player = await new_player(event)

# if options.stop:
#     if (not game.player_red or game.player_red != player) and (
#         not game.player_black or game.player_black != player
#     ):
#         await send("只有游戏参与者才能结束游戏")
#     stop_game(cid)
#     await send("游戏已结束，可发送“重载象棋棋局”继续下棋")

# if options.show:
#     await send((game.draw(),))

# if (
#     game.player_red
#     and game.player_black
#     and game.player_red != player
#     and game.player_black != player
# ):
#     await send("当前有正在进行的游戏")

# if options.repent:
#     if len(game.history) <= 1 or not game.player_next:
#         await send("对局尚未开始")
#     if game.is_battle:
#         if game.player_last and game.player_last != player:
#             await send("上一手棋不是你所下")
#         game.pop()
#     else:
#         if len(game.history) <= 2 and game.player_last != player:
#             await send("上一手棋不是你所下")
#         game.pop()
#         game.pop()
#     await game.save_record(cid)
#     await send((f"{player} 进行了悔棋", game.draw()))

# if (game.player_next and game.player_next != player) or (
#     game.player_last and game.player_last == player
# ):
#     await send("当前不是你的回合")

# move = options.move
# if not match_move(move):
#     await send("发送 中文纵线格式如“炮二平五” 或 起始坐标格式如“h2e2” 下棋")

# try:
#     move = Move.from_ucci(move)
# except ValueError:
#     try:
#         move = Move.from_chinese(game, move)
#     except ValueError:
#         await send("请发送正确的走法，如 “炮二平五” 或 “h2e2”")

# try:
#     move_str = move.chinese(game)
# except ValueError:
#     await send("不正确的走法")

# result = game.push(move)
# if result == MoveResult.ILLEAGAL:
#     await send("不正确的走法")
# elif result == MoveResult.CHECKED:
#     await send("该走法将导致被将军或白脸将")

# msgs: List[Union[str, BytesIO]] = []

# if not game.player_last:
#     if not game.player_red:
#         game.player_red = player
#     elif not game.player_black:
#         game.player_black = player
#     msg = f"{player} 加入了游戏并下出 {move_str}"
# else:
#     msg = f"{player} 下出 {move_str}"

# if result == MoveResult.RED_WIN:
#     stop_game(cid)
#     if game.is_battle:
#         msg += f"，恭喜 {game.player_red} 获胜！"
#     else:
#         msg += "，恭喜你赢了！" if player == game.player_red else "，很遗憾你输了！"
# elif result == MoveResult.BLACK_WIN:
#     stop_game(cid)
#     if game.is_battle:
#         msg += f"，恭喜 {game.player_black} 获胜！"
#     else:
#         msg += "，恭喜你赢了！" if player == game.player_black else "，很遗憾你输了！"
# elif result == MoveResult.DRAW:
#     stop_game(cid)
#     msg += f"，本局游戏平局"
# else:
#     if game.player_next and game.is_battle:
#         msg += f"，下一手轮到 {game.player_next}"

# msgs.append(msg)

# if game.is_battle:
#     msgs.append(game.draw())
# else:
#     msgs.append(game.draw(False))
#     if not result:
#         ai_player = game.player_next
#         assert isinstance(ai_player, AiPlayer)
#         move = await ai_player.get_move(game.position())
#         move_chi = move.chinese(game)
#         result = game.push(move)

#         msg = f"{ai_player} 下出 {move_chi}"
#         if result == MoveResult.ILLEAGAL:
#             game.pop()
#             await send("象棋引擎出错，请结束游戏或稍后再试")
#         elif result:
#             stop_game(cid)
#             if result == MoveResult.CHECKED:
#                 msg += "，恭喜你赢了！"
#             elif result == MoveResult.RED_WIN:
#                 msg += "，恭喜你赢了！" if player == game.player_red else "，很遗憾你输了！"
#             elif result == MoveResult.BLACK_WIN:
#                 msg += "，恭喜你赢了！" if player == game.player_black else "，很遗憾你输了！"
#             elif result == MoveResult.DRAW:
#                 msg += f"，本局游戏平局"
#         msgs.append(msg)
#         msgs.append(game.draw())

# await game.save_record(cid)
# await send(msgs)
