import uuid
from datetime import datetime
from typing import Optional

import chess
import chess.engine
import chess.svg
from chess import Board, Move
import cairosvg


# from .model import GameRecord


class Player:
    def __init__(self, id: int, name: str):
        """
        @id: qq号
        @name: 群昵称/QQ昵称
        """
        self.id = id
        self.name = name

    def __eq__(self, player: "Player") -> bool:
        if not isinstance(player, Player): return False
        return self.id == player.id

    def __str__(self) -> str:
        return self.name


class Game:
    def __init__(self):
        self.board = Board()
        self.player_white: Optional[Player] = None
        self.player_black: Optional[Player] = None
        self.id: str = uuid.uuid4().hex
        self.start_time = datetime.now()
        self.update_time = datetime.now()

    @property
    def player_next(self) -> Optional[Player]:
        if self.board.turn == chess.WHITE:
            return self.player_white
        else:
            return self.player_black

    @property
    def player_last(self) -> Optional[Player]:
        if self.board.turn == chess.WHITE:
            return self.player_black
        else:
            return self.player_white

    def draw(self) -> bytes:
        lastmove = self.board.move_stack[-1] if self.board.move_stack else None
        check = lastmove.to_square if lastmove and self.board.is_check() else None
        svg = chess.svg.board(
            self.board,
            orientation=self.board.turn,
            lastmove=lastmove,
            check=check,
            size=1000,
        )
        with open('/root/code/LittleUnicorn/2.0/chess.svg', 'w') as f:
            f.write(svg)
        return cairosvg.svg2png(bytestring=svg, output_width=500, output_height=500, )

    def push(self, move: chess.Move) -> bool:
        try:
            self.board.push_uci(move)
            return True
        except ValueError:
            return False

    def outcome(self) -> Optional[chess.Outcome]:
        return self.board.outcome()

    def fen(self) -> str:
        return self.board.fen()
    # def save_record(self, session_id: str)->GameRecord:
    #     record = GameRecord(game_id=self.id, session_id=session_id)
    #     if self.player_white:
    #         record.player_white_id = str(self.player_white.id)
    #         record.player_white_name = self.player_white.name
    #     if self.player_black:
    #         record.player_black_id = str(self.player_black.id)
    #         record.player_black_name = self.player_black.name
    #     record.start_time = self.start_time
    #     self.update_time = datetime.now()
    #     record.update_time = self.update_time
    #     record.start_fen = self.board.starting_fen
    #     record.moves = " ".join([str(move) for move in self.board.move_stack])
    #     record.is_game_over = self.board.is_game_over()
    #     return record
    # @classmethod
    # async def load_record(cls, session_id: str) -> Optional["Game"]:
    #     async def load_player(
    #         id: str, name: str, is_ai: bool = False, level: int = 0
    #     ) -> Optional[Player]:
    #         if not id:
    #             return None
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
    #     game.player_white = await load_player(
    #         record.player_white_id,
    #         record.player_white_name,
    #         record.player_white_is_ai,
    #         record.player_white_level,
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
    #     game.board = Board(start_fen)
    #     for move in record.moves.split(" "):
    #         if move:
    #             game.board.push_uci(move)
    #     return game
