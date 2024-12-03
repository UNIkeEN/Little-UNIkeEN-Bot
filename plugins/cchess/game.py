import uuid
from datetime import datetime
from typing import Optional, Dict


from .board import Board
from .config import Config
from .engine import Engine, UciEngine, UcciEngine, EngineError
# from model import GameRecord
from .move import Move

class Player:
    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name

    def __eq__(self, player: "Player") -> bool:
        return player != None and self.id == player.id

    def __str__(self) -> str:
        return self.name


class AiPlayer(Player):
    def __init__(self, id:int, engineType:str, level: int, engine_path: str, options:Dict[str, str] = {}):
        self.level = level
        name = f"小马 lv.{level}"
        if engineType == 'uci':
            self.engine = UciEngine(engine_path)
        elif engineType == 'ucci':
            self.engine = UcciEngine(engine_path)
        else:
            raise EngineError("unknown engine type: {}".format(engineType))
        self.time = [100, 400, 700, 1000, 1500, 2500, 5000, 8000, 10000][level - 1]
        self.skill = [1, 2, 3, 4, 6, 10, 12, 15, 20][level - 1]
        self.depth = [2, 3, 3, 4, 5, 7, 10, 17, 25][level - 1]
        self.options = options
        self.options.update({
            'Skill Level': str(self.skill)
        })
        self.engineType = engineType
        super().__init__(id, name)
        self.init_engine()

    def get_move(self, position: str) -> Move:
        return self.engine.bestmove(position, time=self.time, depth=self.depth)

    def init_engine(self):
        self.engine.open()
        self.engine.set_options(self.options)
        self.engine.make_ready()

class Game(Board):
    def __init__(self):
        super().__init__()
        self.player_red: Optional[Player] = None
        self.player_black: Optional[Player] = None
        self.id: str = uuid.uuid4().hex
        self.start_time = datetime.now()
        self.update_time = datetime.now()

    @property
    def player_next(self) -> Optional[Player]:
        return self.player_red if self.moveside else self.player_black

    @property
    def player_last(self) -> Optional[Player]:
        return self.player_black if self.moveside else self.player_red

    @property
    def is_battle(self) -> bool:
        return not isinstance(self.player_red, AiPlayer) and not isinstance(
            self.player_black, AiPlayer
        )

    def close_engine(self):
        if isinstance(self.player_red, AiPlayer):
            self.player_red.engine.close()
        if isinstance(self.player_black, AiPlayer):
            self.player_black.engine.close()

    # async def save_record(self, session_id: str):
    #     statement = select(GameRecord).where(GameRecord.game_id == self.id)
    #     async with create_session() as session:
    #         record: Optional[GameRecord] = await session.scalar(statement)
    #         if not record:
    #             record = GameRecord(game_id=self.id, session_id=session_id)
    #         if self.player_red:
    #             record.player_red_id = str(self.player_red.id)
    #             record.player_red_name = self.player_red.name
    #             if isinstance(self.player_red, AiPlayer):
    #                 record.player_red_is_ai = True
    #                 record.player_red_level = self.player_red.level
    #         if self.player_black:
    #             record.player_black_id = str(self.player_black.id)
    #             record.player_black_name = self.player_black.name
    #             if isinstance(self.player_black, AiPlayer):
    #                 record.player_black_is_ai = True
    #                 record.player_black_level = self.player_black.level
    #         record.start_time = self.start_time
    #         self.update_time = datetime.now()
    #         record.update_time = self.update_time
    #         record.start_fen = self.start_fen
    #         record.moves = " ".join([str(move) for move in self.moves])
    #         record.is_game_over = self.is_game_over()
    #         session.add(record)
    #         await session.commit()

    # @classmethod
    # async def load_record(cls, session_id: str) -> Optional["Game"]:
    #     async def load_player(
    #         id: str, name: str, is_ai: bool = False, level: int = 0
    #     ) -> Optional[Player]:
    #         if not id:
    #             return None
    #         if is_ai:
    #             if not (1 <= level <= 8):
    #                 level = 4
    #             player = AiPlayer(level)
    #             player.id = id
    #             player.name = name
    #             await player.engine.open()
    #             return player
    #         else:
    #             return Player(id, name)

    #     statement = select(GameRecord).where(
    #         GameRecord.session_id == session_id, GameRecord.is_game_over == False
    #     )
    #     async with create_session() as session:
    #         records = (await session.scalars(statement)).all()
    #     if not records:
    #         return None
    #     record = sorted(records, key=lambda x: x.update_time)[-1]
    #     game = cls()
    #     game.id = record.game_id
    #     game.player_red = await load_player(
    #         record.player_red_id,
    #         record.player_red_name,
    #         record.player_red_is_ai,
    #         record.player_red_level,
    #     )
    #     game.player_black = await load_player(
    #         record.player_black_id,
    #         record.player_black_name,
    #         record.player_black_is_ai,
    #         record.player_black_level,
    #     )
    #     game.start_time = record.start_time
    #     game.update_time = record.update_time
    #     start_fen = record.start_fen
    #     moves = [Move.from_ucci(move) for move in record.moves.split(" ") if move]
    #     game.from_fen(start_fen)
    #     for move in moves:
    #         game.push(move)
    #     return game
