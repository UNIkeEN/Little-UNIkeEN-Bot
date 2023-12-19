import re
from typing import Dict, Union, Any, Optional

import chess
from chess import Termination, Move
from .game import Game, Player
from io import BytesIO
from utils.basicEvent import send, warning
from utils.standardPlugin import StandardPlugin
from utils.basicConfigs import sqlConfig, ROOT_PATH, SAVE_TMP_PATH
import os
from PIL import Image
class ChessHelper(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any)->bool:
        return msg in ['象棋帮助']
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        send(target, (
            '象棋帮助：象棋帮助\n'
            '执白发起游戏：象棋, -lxq\n'
            '执黑发起游戏：执黑下象棋\n'
            '接受游戏：应战\n'
            '认输：   认输\n'
            '下棋： e7e8/e7e8q\n'
            '在坐标后加棋子字母表示升变，如“e7e8q”表示升变为后\n'
            '悔棋： 悔棋\n'
            '棋子： \n'
            '♖R ♘N ♗B ♕Q ♔K ♙P\n'
            '♜r ♞n ♝b ♛q ♚k ♟p'
        ), data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'ChessHelper',
            'description': '国际象棋帮助',
            'commandDescription': '象棋帮助',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }



class ChessPlugin(StandardPlugin):
    def __init__(self):
        self.startCommands = ['下象棋', '-lxq', '执黑下象棋']
        self.acceptCommands = ['应战']
        self.defeatCommands = ['认输', '掀棋盘', '不下了', '结束对局']
        self.ckptCommands = ['保存对局']
        self.chessdbCommands = ['谱招', '谱着']
        self.games:Dict[int, Game] = {}
        self.matchMovePattern = re.compile(r"^[a-zA-Z]\d[a-zA-Z]\d[a-zA-Z]?$")
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
                    game.player_white = player
                    send(target, '群友 {} 执白，向大家发起国际象棋挑战，输入“应战”接受挑战吧！'.format(player), data['message_type'])
                else:
                    game.player_black = player
                    send(target, '群友 {} 执黑，向大家发起国际象棋挑战，输入“应战”接受挑战吧！'.format(player), data['message_type'])
                self.games[target] = game
        elif msg in self.ckptCommands:
            game = self.games.get(group_id, None)
            if game == None:
                send(target, '[CQ:reply,id={}]尚未有人发起战斗，请输入 下象棋、-lxq、执黑下象棋 发起挑战'.format(data['message_id']), data['message_type'])
            else:
                fen = game.fen()
                send(target, fen, data['message_type'])
        elif msg in self.acceptCommands:
            game = self.games.get(group_id, None)
            if game == None:
                send(target, '[CQ:reply,id={}]尚未有人发起战斗，请输入 下象棋、-lxq、执黑下象棋 发起挑战'.format(data['message_id']), data['message_type'])
            elif game.player_white != None and game.player_black != None:
                send(target, '[CQ:reply,id={}]对局正在进行中，请耐心等待'.format(data['message_id']), data['message_type'])
            elif (game.player_white == None) ^ (game.player_black == None):
                player = self.new_player(data)
                if game.player_white == None:
                    if game.player_black.id == player.id:
                        send(target, '[CQ:reply,id={}]自己不能和自己下棋'.format(data['message_id']), data['message_type'])
                    else:
                        game.player_white = player
                        imgPath = self.draw_board(game, data)
                        send(target, f'[CQ:image,file=file:///{imgPath}]对局开始，请执白者 [CQ:at,qq={game.player_white.id}] 先行', data['message_type'])
                else:
                    if game.player_white.id == player.id:
                        send(target, '[CQ:reply,id={}]自己不能和自己下棋'.format(data['message_id']), data['message_type'])
                    else:
                        game.player_black = player
                        imgPath = self.draw_board(game, data)
                        send(target, f'[CQ:image,file=file:///{imgPath}]对局开始，请执白者 [CQ:at,qq={game.player_white.id}] 先行', data['message_type'])
            else: 
                send(target, '[CQ:reply,id={}]内部错误 game.player_white == None and game.player_black == None'.format(data['message_id']), data['message_type'])
                warning("国际象棋 game.player_white == None and game.player_black == None in group %d"%(target))
        elif msg in self.defeatCommands:
            game = self.games.get(group_id, None)
            if game == None:
                send(target, '[CQ:reply,id={}]群内没有对局，请先发起对局'.format(data['message_id']), data['message_type'])
            elif (game.player_white == None) ^ (game.player_black == None):
                if game.player_white != None and game.player_white.id == user_id:
                    send(target, '没有成员应战，对局结束', data['message_type'])
                    self.stop_game(data)
                elif game.player_black != None and game.player_black.id == user_id:
                    send(target, '没有成员应战，对局结束', data['message_type'])
                    self.stop_game(data)
                else:
                    send(target, '[CQ:reply,id={}]请先应战'.format(data['message_id']), data['message_type'])
            elif game.player_white != None and game.player_black != None:
                if game.player_white.id == user_id:
                    send(target, '白方认输，恭喜 {} 获胜！'.format(game.player_black), data['message_type'])
                    self.stop_game(data)
                elif game.player_black.id == user_id:
                    send(target, '黑方认输，恭喜 {} 获胜！'.format(game.player_white), data['message_type'])
                    self.stop_game(data)
                else:
                    send(target, '[CQ:reply,id={}]对局正在进行中，请耐心等待'.format(data['message_id']), data['message_type'])
            else:
                send(target, '[CQ:reply,id={}]内部错误 game.player_white == None and game.player_black == None'.format(data['message_id']), data['message_type'])
                warning("国际象棋 game.player_white == None and game.player_black == None in group %d"%(target))
        elif self.match_move(msg):
            game = self.games.get(group_id, None)
            if game == None:
                if self.get_move(msg, game) != None:
                    send(target, '[CQ:reply,id={}]群内没有对局，请先发起对局'.format(data['message_id']), data['message_type'])
            elif game.player_black == None or game.player_white == None:
                if self.get_move(msg, game) != None:
                    send(target, '[CQ:reply,id={}]游戏尚未开始，请先回复“应战”接受对局'.format(data['message_id']), data['message_type'])
            elif game.player_next != None and game.player_next.id != user_id:
                if self.get_move(msg, game) != None:
                    send(target, '[CQ:reply,id={}]不是你的回合'.format(data['message_id']), data['message_type'])
            else:
                if self.get_move(msg, game) == None:
                    send(target, "[CQ:reply,id={}]请发送正确的走法，如 “h2e2”".format(data['message_id']), data['message_type'])
                elif not game.push(msg):
                    send(target, "[CQ:reply,id={}]不正确的走法，请重新输入".format(data['message_id']), data['message_type'])
                else:
                    result = game.outcome()
                    if result == None:
                        imgPath = self.draw_board(game, data)
                        send(target, f'[CQ:image,file=file:///{imgPath}]下一手轮到 {game.player_next} 行棋', data['message_type'])
                    # elif result == MoveResult.CHECKED:
                    #     send(target, "不能送将，请改变招法".format(data['message_id']), data['message_type'])
                    elif result.winner == chess.WHITE:
                        imgPath = self.draw_board(game, data)
                        send(target, f'[CQ:image,file=file:///{imgPath}]黑方被将死，恭喜 {game.player_white} 获胜！', data['message_type'])
                        self.stop_game(data)
                    elif result.winner == chess.BLACK:
                        imgPath = self.draw_board(game, data)
                        send(target, f'[CQ:image,file=file:///{imgPath}]白方被将死，恭喜 {game.player_black} 获胜！', data['message_type'])
                        self.stop_game(data)
                    elif result.winner == None:
                        send(target, "根据规则，局面判和", data['message_type'])
                        self.stop_game(data)
                    else:
                        imgPath = self.draw_board(game, data)
                        send(target, f'[CQ:image,file=file:///{imgPath}]下一手轮到 {game.player_next} 行棋', data['message_type'])
        elif msg in self.chessdbCommands:
            game = self.games.get(group_id, None)
            if game == None:
                send(target, '[CQ:reply,id={}]群内没有对局，请先发起对局'.format(data['message_id']), data['message_type'])
            # elif len(game.history) <= 1:
            #     send(target, '[CQ:reply,id={}]对局尚未开始'.format(data['message_id']), data['message_type'])
            else:
                imgPath = self.draw_chessdb(game, data)
                if imgPath != None:
                    send(target, f'[CQ:image,file=file:///{imgPath}]', data['message_type'])
                else:
                    send(target, f"[CQ:reply,id={data['message_id']}]查询失败", data['message_type'])
        return 'OK'
    def match_move(self, msg:str)->bool:
        return self.matchMovePattern.match(msg) != None
    def get_move(self, msg, _)->Optional[Move]:
        try:
            move = Move.from_uci(msg)
            return move
        except ValueError:
            return None
    def getPluginInfo(self, )->Any:
        return {
            'name': 'ChessPlugin',
            'description': '国际象棋',
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

    def draw_board(self, game:Game, data:Dict[str, Any])->str:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        imgPath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'chess_%d.png'%(data['group_id']))
        Image.open(BytesIO(game.draw())).save(imgPath)
        return imgPath
    def draw_chessdb(self, game, data)->Optional[str]:
        raise NotImplementedError
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        imgPath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'chessdb_%d.png'%(data['group_id']))
        result = drawChessdb(game, imgPath)
        if result:
            return imgPath
        else:
            return None


# def get_move_input(state: T_State, msg: str = EventPlainText()) -> bool:
#     if match_move(msg):
#         state["move"] = msg
#         return True
#     return False


# move_matcher = on_message(Rule(game_running) & get_move_input, block=True, priority=14)


# @move_matcher.handle()
# async def _(
#     bot: Bot,
#     matcher: Matcher,
#     event: Event,
#     state: T_State,
# ):
#     move: str = state["move"]
#     await handle_chess(bot, matcher, event, [move])


# async def stop_game(cid: str):
#     game = games.pop(cid, None)
#     if game:
#         await game.close_engine()


# async def stop_game_timeout(matcher: Matcher, cid: str):
#     timers.pop(cid, None)
#     if games.get(cid, None):
#         games.pop(cid)
#         await matcher.finish("国际象棋下棋超时，游戏结束，可发送“重载国际象棋棋局”继续下棋")


# def set_timeout(matcher: Matcher, cid: str, timeout: float = 600):
#     timer = timers.get(cid, None)
#     if timer:
#         timer.cancel()
#     loop = asyncio.get_running_loop()
#     timer = loop.call_later(
#         timeout, lambda: asyncio.ensure_future(stop_game_timeout(matcher, cid))
#     )
#     timers[cid] = timer


# async def handle_chess(
#     bot: Bot,
#     matcher: Matcher,
#     event: Event,
#     argv: List[str],
# ):
#     async def new_player(event: Event) -> Player:
#         user_id = event.get_user_id()
#         user_name = ""
#         if user_info := await get_user_info(bot, event, user_id=user_id):
#             user_name = user_info.user_name
#         return Player(user_id, user_name)

#     async def send(msgs: Union[str, Iterable[Union[str, bytes]]] = "") -> NoReturn:
#         if not msgs:
#             await matcher.finish()
#         if isinstance(msgs, str):
#             await matcher.finish(msgs)

#         msg_builder = MessageFactory([])
#         for msg in msgs:
#             if isinstance(msg, bytes):
#                 msg_builder.append(Image(msg))
#             else:
#                 msg_builder.append(msg)
#         await msg_builder.send()
#         await matcher.finish()

#     try:
#         args = parser.parse_args(argv)
#     except ParserExit as e:
#         if e.status == 0:
#             await matcher.finish(__plugin_meta__.usage)
#         await matcher.finish()

#     options = Options(**vars(args))

#     cid = get_cid(bot, event)
#     if not games.get(cid, None):
#         if options.move:
#             await send()

#         if options.stop or options.show or options.repent:
#             await send("没有正在进行的游戏")

#         if not options.battle and not 1 <= options.level <= 8:
#             await send("等级应在 1~8 之间")

#         if options.reload:
#             try:
#                 game = await Game.load_record(cid)
#             except FileNotFoundError:
#                 await send("国际象棋引擎加载失败，请检查设置")
#             if not game:
#                 await send("没有找到被中断的游戏")
#             games[cid] = game
#             await send(
#                 (
#                     (
#                         f"游戏发起时间：{game.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
#                         f"白方：{game.player_white}\n"
#                         f"黑方：{game.player_black}\n"
#                         f"下一手轮到：{game.player_next}\n"
#                     ),
#                     await game.draw(),
#                 )
#             )

#         game = Game()
#         player = await new_player(event)
#         if options.black:
#             game.player_black = player
#         else:
#             game.player_white = player

#         msg = f"{player} 发起了游戏 国际象棋！\n发送 起始坐标格式 如“e2e4”下棋，在坐标后加棋子字母表示升变，如“e7e8q”"

#         if not options.battle:
#             try:
#                 ai_player = AiPlayer(options.level)
#                 await ai_player.open_engine()

#                 if options.black:
#                     game.player_white = ai_player
#                     move = await ai_player.get_move(game.board)
#                     if not move:
#                         await send("国际象棋引擎返回不正确，请检查设置")
#                     game.board.push_uci(move.uci())
#                     msg += f"\n{ai_player} 下出 {move}"
#                 else:
#                     game.player_black = ai_player
#             except:
#                 await send("国际象棋引擎加载失败，请检查设置")

#         games[cid] = game
#         set_timeout(matcher, cid)
#         await game.save_record(cid)
#         await send((msg + "\n", await game.draw()))

#     game = games[cid]
#     set_timeout(matcher, cid)
#     player = await new_player(event)

#     if options.stop:
#         if (not game.player_white or game.player_white != player) and (
#             not game.player_black or game.player_black != player
#         ):
#             await send("只有游戏参与者才能结束游戏")
#         await stop_game(cid)
#         await send("游戏已结束，可发送“重载国际象棋棋局”继续下棋")

#     if options.show:
#         await send((await game.draw(),))

#     if (
#         game.player_white
#         and game.player_black
#         and game.player_white != player
#         and game.player_black != player
#     ):
#         await send("当前有正在进行的游戏")

#     if options.repent:
#         if len(game.board.move_stack) <= 0 or not game.player_next:
#             await send("对局尚未开始")
#         if game.is_battle:
#             if game.player_last and game.player_last != player:
#                 await send("上一手棋不是你所下")
#             game.board.pop()
#         else:
#             if len(game.board.move_stack) <= 1 and game.player_last != player:
#                 await send("上一手棋不是你所下")
#             game.board.pop()
#             game.board.pop()
#         await game.save_record(cid)
#         await send((f"{player} 进行了悔棋\n", await game.draw()))

#     if (game.player_next and game.player_next != player) or (
#         game.player_last and game.player_last == player
#     ):
#         await send("当前不是你的回合")

#     move = options.move
#     if not match_move(move):
#         await send("发送 起始坐标格式，如“e2e4”下棋")

#     try:
#         game.board.push_uci(move.lower())
#         result = game.board.outcome()
#     except ValueError:
#         await send("不正确的走法")

#     msgs: List[Union[str, bytes]] = []

#     if not game.player_last:
#         if not game.player_white:
#             game.player_white = player
#         elif not game.player_black:
#             game.player_black = player
#         msg = f"{player} 加入了游戏并下出 {move}"
#     else:
#         msg = f"{player} 下出 {move}"

#     if game.board.is_game_over():
#         await stop_game(cid)
#         if result == Termination.CHECKMATE:
#             winner = result.winner
#             assert winner is not None
#             if game.is_battle:
#                 msg += (
#                     f"，恭喜 {game.player_white} 获胜！"
#                     if winner == chess.WHITE
#                     else f"，恭喜 {game.player_black} 获胜！"
#                 )
#             else:
#                 msg += "，恭喜你赢了！" if game.board.turn == (not winner) else "，很遗憾你输了！"
#         elif result in [Termination.INSUFFICIENT_MATERIAL, Termination.STALEMATE]:
#             msg += f"，本局游戏平局"
#         else:
#             msg += f"，游戏结束"
#     else:
#         if game.player_next and game.is_battle:
#             msg += f"，下一手轮到 {game.player_next}"
#     msgs.append(msg + "\n")
#     msgs.append(await game.draw())

#     if not game.is_battle:
#         if not game.board.is_game_over():
#             ai_player = game.player_next
#             assert isinstance(ai_player, AiPlayer)
#             try:
#                 move = await ai_player.get_move(game.board)
#                 if not move:
#                     await send("国际象棋引擎出错，请结束游戏或稍后再试")
#                 game.board.push_uci(move.uci())
#                 result = game.board.outcome()
#             except:
#                 await send("国际象棋引擎出错，请结束游戏或稍后再试")

#             msg = f"\n{ai_player} 下出 {move}"
#             if game.board.is_game_over():
#                 await stop_game(cid)
#                 if result == Termination.CHECKMATE:
#                     winner = result.winner
#                     assert winner is not None
#                     msg += "，恭喜你赢了！" if game.board.turn == (not winner) else "，很遗憾你输了！"
#                 elif result in [
#                     Termination.INSUFFICIENT_MATERIAL,
#                     Termination.STALEMATE,
#                 ]:
#                     msg += f"，本局游戏平局"
#                 else:
#                     msg += f"，游戏结束"
#             msgs.append(msg + "\n")
#             msgs.append((await game.draw()))

#     await game.save_record(cid)
#     await send(msgs)
