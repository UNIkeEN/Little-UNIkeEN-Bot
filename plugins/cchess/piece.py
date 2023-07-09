from enum import Enum
from typing import Dict, Tuple


class PieceType(Enum):
    KING = "k"
    """将"""
    ADVISOR = "a"
    """士"""
    BISHOP = "b"
    """象"""
    KNIGHT = "n"
    """马"""
    ROOK = "r"
    """车"""
    CANNON = "c"
    """炮"""
    PAWN = "p"
    """兵"""


piece_data: Dict[str, Tuple[Tuple[str, str], Tuple[str, str]]] = {
    "k": (("帅", "将"), ("\U0001FA00", "\U0001FA07")),
    "a": (("仕", "士"), ("\U0001FA01", "\U0001FA08")),
    "b": (("相", "象"), ("\U0001FA02", "\U0001FA09")),
    "n": (("马", "马"), ("\U0001FA03", "\U0001FA0A")),
    "r": (("车", "车"), ("\U0001FA04", "\U0001FA0B")),
    "c": (("炮", "炮"), ("\U0001FA05", "\U0001FA0C")),
    "p": (("兵", "卒"), ("\U0001FA06", "\U0001FA0D")),
}


class Piece:
    def __init__(self, symbol: str):
        self.symbol: str = symbol
        """棋子字母表示，大写表示红方，小写表示黑方"""
        s = symbol.lower()
        t = 1 if s == symbol else 0
        self.name: str = piece_data[s][0][t]
        """棋子中文名称"""
        self.unicode_symbol: str = piece_data[s][1][t]
        """棋子 Unicode 符号"""
        self.piece_type: PieceType = PieceType(s)
        """棋子类型"""
        self.color: bool = bool(t == 0)
        """棋子颜色，`True`为红色，`False`为黑色"""

    def __str__(self) -> str:
        return self.symbol
