import re
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from typing import Iterator, List, Optional

from .drawer import draw_board
from .move import Move, Pos
from .piece import Piece, PieceType

INIT_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"


class MoveResult(Enum):
    RED_WIN = 0
    """红胜"""
    BLACK_WIN = 1
    """黑胜"""
    DRAW = 2
    """平局"""
    ILLEAGAL = 3
    """移动不合法"""
    CHECKED = 4
    """移动会导致被将军"""

    @classmethod
    def from_bool(cls, moveside: bool) -> "MoveResult":
        """当前行动方判负"""
        return MoveResult.BLACK_WIN if moveside else MoveResult.RED_WIN


@dataclass
class History:
    fen: str
    """当前局面的FEN字符串"""
    latest_fen: str
    """上一个不吃子局面FEN字符串"""
    latest_moves: List[Move]
    """从上一个不吃子局面开始的移动"""


class Board:
    def __init__(self, start_fen: str = INIT_FEN):
        self._board: List[List[Optional[Piece]]] = [
            [None for j in range(9)] for i in range(10)
        ]
        self.moveside: bool = True
        """当前行动方，`True`为红方，`False`为黑方"""
        self.halfmove: int = 0
        """双方没有吃子的走棋步数(半回合数)"""
        self.fullmove: int = 1
        """当前的回合数"""
        self.start_fen: str = start_fen
        """起始局面FEN字符串"""
        self.moves: List[Move] = []
        """记录所有移动"""
        self.latest_fen: str = start_fen
        """上一个不吃子局面FEN字符串"""
        self.latest_moves: List[Move] = []
        """从上一个不吃子局面开始的移动"""
        self.from_fen(start_fen)
        self.history: List[History] = []
        """历史记录"""
        self.save_history()

    def __str__(self) -> str:
        return self.fen()

    @property
    def last_move(self) -> Move:
        """上一次的移动"""
        return self.moves[-1] if self.moves else Move.null()

    def from_fen(self, fen: str = ""):
        """从FEN字符串读取当前局面"""
        board_fen, moveside, _, _, halfmove, fullmove = fen.split(" ")

        self._board = [[None for j in range(9)] for i in range(10)]
        for i, line_fen in enumerate(board_fen.split("/")[::-1]):
            j = 0
            for ch in line_fen:
                if ch.isdigit():
                    num = int(ch)
                    if 1 <= num <= 9:
                        j += num
                elif re.fullmatch(r"[kabnrcpKABNRCP]", ch):
                    self._board[i][j] = Piece(ch)
                    j += 1
                else:
                    raise ValueError("Illegal character in fen string!")

        self.moveside = not (moveside == "b")
        self.halfmove = int(halfmove)
        self.fullmove = int(fullmove)

    def fen(self) -> str:
        """返回当前局面的FEN字符串"""
        moveside = "w" if self.moveside else "b"
        return f"{self.board_fen()} {moveside} - - {self.halfmove} {self.fullmove}"

    def board_fen(self) -> str:
        """返回当前棋盘布局的FEN字符串"""
        line_fens = []
        for line in self._board:
            line_fen = ""
            num = 0
            for piece in line:
                if not piece:
                    num += 1
                else:
                    if num:
                        line_fen += str(num)
                    num = 0
                    line_fen += piece.symbol
            if num:
                line_fen += str(num)
            line_fens.append(line_fen)
        return "/".join(line_fens[::-1])

    def get_piece_at(self, pos: Pos, sameside: bool = True) -> Optional[Piece]:
        """获取指定位置的棋子"""
        piece = self._board[pos.x][pos.y]
        if piece and (
                (self.moveside == piece.color)
                if sameside
                else (self.moveside != piece.color)
        ):
            return piece

    def get_piece_pos(
            self, piece_type: Optional[PieceType] = None, sameside: bool = True
    ) -> Iterator[Pos]:
        """获取指定类型的棋子，`piece_type`为空表示所有类型"""
        for row, line in enumerate(self._board):
            for col, piece in enumerate(line):
                if (
                        piece
                        and (piece_type is None or piece.piece_type == piece_type)
                        and (
                        (self.moveside == piece.color)
                        if sameside
                        else (self.moveside != piece.color)
                )
                ):
                    yield Pos(row, col)

    def get_piece(self, pos: Pos) -> Optional[Piece]:
        """获取棋子"""
        return self._board[pos.x][pos.y]

    def set_piece(self, pos: Pos, piece: Optional[Piece]):
        """设置棋子"""
        self._board[pos.x][pos.y] = piece

    def legal_to_pos(self, from_pos: Pos) -> Iterator[Pos]:
        """获取某个位置的棋子所有可能走的位置"""
        piece = self.get_piece(from_pos)
        if not piece:
            return
        sameside = piece.color == self.moveside
        self_pos = list(self.get_piece_pos(sameside=sameside))
        oppo_pos = list(self.get_piece_pos(sameside=not sameside))
        total_pos = self_pos + oppo_pos

        piece_type = piece.piece_type
        if piece_type == PieceType.KING:
            for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
                to_pos = Pos(from_pos.x + dx, from_pos.y + dy)
                if (
                        (0 <= to_pos.x <= 2 or 7 <= to_pos.x <= 9)
                        and 3 <= to_pos.y <= 5
                        and to_pos not in self_pos
                ):
                    yield to_pos
        elif piece_type == PieceType.ADVISOR:
            for dx, dy in ((1, 1), (-1, -1), (1, -1), (-1, 1)):
                to_pos = Pos(from_pos.x + dx, from_pos.y + dy)
                if (
                        (0 <= to_pos.x <= 2 or 7 <= to_pos.x <= 9)
                        and 3 <= to_pos.y <= 5
                        and to_pos not in self_pos
                ):
                    yield to_pos
        elif piece_type == PieceType.BISHOP:
            for dx, dy in ((2, 2), (-2, -2), (2, -2), (-2, 2)):
                to_pos = Pos(from_pos.x + dx, from_pos.y + dy)
                mid_pos = Pos(
                    (from_pos.x + to_pos.x) // 2, (from_pos.y + to_pos.y) // 2
                )
                if (
                        to_pos.valid()
                        and mid_pos.x not in [4, 5]
                        and to_pos not in self_pos
                        and mid_pos not in total_pos
                ):
                    yield to_pos
        elif piece_type == PieceType.KNIGHT:
            for dx, dy in (
                    (2, 1),
                    (-2, -1),
                    (-2, 1),
                    (2, -1),
                    (1, 2),
                    (-1, -2),
                    (-1, 2),
                    (1, -2),
            ):
                to_pos = Pos(from_pos.x + dx, from_pos.y + dy)
                if abs(dx) == 1:
                    mid_pos = Pos(from_pos.x, (from_pos.y + to_pos.y) // 2)
                else:
                    mid_pos = Pos((from_pos.x + to_pos.x) // 2, from_pos.y)
                if (
                        to_pos.valid()
                        and to_pos not in self_pos
                        and mid_pos not in total_pos
                ):
                    yield to_pos
        elif piece_type == PieceType.PAWN:
            if self.moveside:
                if from_pos.x >= 5:
                    moves = ((1, 0), (0, 1), (0, -1))
                else:
                    moves = ((1, 0),)
            else:
                if from_pos.x <= 4:
                    moves = ((-1, 0), (0, 1), (0, -1))
                else:
                    moves = ((-1, 0),)
            for dx, dy in moves:
                to_pos = Pos(from_pos.x + dx, from_pos.y + dy)
                if to_pos.valid() and to_pos not in self_pos:
                    yield to_pos
        elif piece_type == PieceType.ROOK:
            start_x = 0
            end_x = 9
            start_y = 0
            end_y = 8
            for pos in total_pos:
                if pos.x == from_pos.x:
                    if start_y < pos.y < from_pos.y:
                        start_y = pos.y
                    if from_pos.y < pos.y < end_y:
                        end_y = pos.y
                if pos.y == from_pos.y:
                    if start_x < pos.x < from_pos.x:
                        start_x = pos.x
                    if from_pos.x < pos.x < end_x:
                        end_x = pos.x
            for x in range(start_x, end_x + 1):
                to_pos = Pos(x, from_pos.y)
                if to_pos != from_pos and to_pos not in self_pos:
                    yield to_pos
            for y in range(start_y, end_y + 1):
                to_pos = Pos(from_pos.x, y)
                if to_pos != from_pos and to_pos not in self_pos:
                    yield to_pos
        elif piece_type == PieceType.CANNON:
            above_pos = [p for p in total_pos if p.y == from_pos.y and p.x > from_pos.x]
            below_pos = [p for p in total_pos if p.y == from_pos.y and p.x < from_pos.x]
            left_pos = [p for p in total_pos if p.x == from_pos.x and p.y < from_pos.y]
            right_pos = [p for p in total_pos if p.x == from_pos.x and p.y > from_pos.y]
            above_pos.sort(key=lambda p: p.x)
            below_pos.sort(key=lambda p: p.x, reverse=True)
            left_pos.sort(key=lambda p: p.y, reverse=True)
            right_pos.sort(key=lambda p: p.y)
            start_x = below_pos[0].x if below_pos else 0
            end_x = above_pos[0].x if above_pos else 9
            start_y = left_pos[0].y if left_pos else 0
            end_y = right_pos[0].y if right_pos else 8
            for x in range(start_x, end_x + 1):
                to_pos = Pos(x, from_pos.y)
                if to_pos != from_pos and to_pos not in total_pos:
                    yield to_pos
            for y in range(start_y, end_y + 1):
                to_pos = Pos(from_pos.x, y)
                if to_pos != from_pos and to_pos not in total_pos:
                    yield to_pos
            if len(above_pos) > 1 and above_pos[1] not in self_pos:
                yield above_pos[1]
            if len(below_pos) > 1 and below_pos[1] not in self_pos:
                yield below_pos[1]
            if len(left_pos) > 1 and left_pos[1] not in self_pos:
                yield left_pos[1]
            if len(right_pos) > 1 and right_pos[1] not in self_pos:
                yield right_pos[1]

    def is_legal_move(self, move: Move) -> bool:
        """判断走法是否合法"""
        if not self.get_piece_at(move.from_pos):
            return False
        return move.to_pos in self.legal_to_pos(move.from_pos)

    def is_checked_move(self, move: Move) -> bool:
        """判断走法是否会造成被将军或主帅面对面"""
        board = self.try_move(move)
        if board.is_king_face_to_face() or board.is_checked():
            return True
        return False

    def legal_moves(self) -> Iterator[Move]:
        """当前行动方所有可能走的走法"""
        for from_pos in self.get_piece_pos():
            for to_pos in self.legal_to_pos(from_pos):
                yield Move(from_pos, to_pos)

    def is_dead(self) -> bool:
        """判断当前行动方的将是否被吃掉"""
        return not list(self.get_piece_pos(PieceType.KING))

    def is_king_face_to_face(self) -> bool:
        """判断将帅是否面对面"""
        pos1 = next(self.get_piece_pos(PieceType.KING))
        pos2 = next(self.get_piece_pos(PieceType.KING, sameside=False))
        start_x = min(pos1.x, pos2.x)
        end_x = max(pos1.x, pos2.x)
        return pos1.y == pos2.y and all(
            [self._board[x][pos1.y] is None for x in range(start_x + 1, end_x)]
        )

    def is_checked(self) -> bool:
        """判断当前行动方是否被将军"""
        pos = next(self.get_piece_pos(PieceType.KING))
        for from_pos in self.get_piece_pos(sameside=False):
            if pos in self.legal_to_pos(from_pos):
                return True
        return False

    def is_checked_dead(self) -> bool:
        """判断当前行动方是否被将死"""
        for move in self.legal_moves():
            board = self.try_move(move)
            if not board.is_king_face_to_face() and not board.is_checked():
                return False
        return True

    def position(self) -> str:
        """获取 ucci position 指令字符串，用于设置棋盘局面"""
        res = f"position fen {self.latest_fen}"
        if self.latest_moves:
            moves = [str(m) for m in self.latest_moves]
            res += f" moves {' '.join(moves)}"
        return res

    def save_history(self):
        """保存历史局面"""
        history = History(
            self.fen(),
            self.latest_fen,
            self.latest_moves.copy(),
        )
        self.history.append(history)

    def load_history(self, history: History):
        """从历史局面恢复"""
        self.from_fen(history.fen)
        self.latest_fen = history.latest_fen
        self.latest_moves = history.latest_moves.copy()

    def make_move(self, move: Move):
        """进行移动"""
        change = self.get_piece_at(move.to_pos, sameside=False)  # 发生吃子
        self.set_piece(move.to_pos, self.get_piece(move.from_pos))
        self.set_piece(move.from_pos, None)
        if not self.moveside:
            self.fullmove += 1
        self.moveside = not self.moveside
        self.moves.append(move)
        if change:
            self.latest_fen = self.fen()
            self.latest_moves.clear()
            self.halfmove = 0
        else:
            self.latest_moves.append(move)
            self.halfmove += 1
        self.save_history()

    def try_move(self, move: Move) -> "Board":
        """尝试移动"""
        board = Board(self.fen())
        board.set_piece(move.to_pos, board.get_piece(move.from_pos))
        board.set_piece(move.from_pos, None)
        return board

    def is_game_over(self) -> bool:
        return (
                self.is_dead()
                or self.is_king_face_to_face()
                or self.halfmove >= 60
                or self.is_checked_dead()
        )

    def push(self, move: Move) -> Optional[MoveResult]:
        """移动并返回结果"""
        if not self.is_legal_move(move):
            return MoveResult.ILLEAGAL
        if self.is_checked_move(move):
            return MoveResult.CHECKED
        self.make_move(move)
        if self.is_dead():
            return MoveResult.from_bool(self.moveside)
        if self.is_king_face_to_face():
            return MoveResult.from_bool(not self.moveside)
        if self.is_checked_dead():
            return MoveResult.from_bool(self.moveside)
        if self.halfmove >= 60:  # 未吃子半回合数超过 60 判和棋
            return MoveResult.DRAW

    def pop(self):
        """撤销上一次移动"""
        self.history.pop()
        self.moves.pop()
        self.load_history(self.history[-1])

    def draw(self, sameside: bool = True) -> BytesIO:
        return draw_board(self, sameside)
