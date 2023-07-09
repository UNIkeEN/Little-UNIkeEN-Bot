from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Optional, Tuple

from .piece import PieceType

if TYPE_CHECKING:
    from .board import Board


NUM_CHI = ["一", "二", "三", "四", "五", "六", "七", "八", "九"]
NUM_DIGIT = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
PIECE_DICT: Dict[str, Tuple[str, ...]] = {
    "k": ("帥", "將", "将", "帅"),
    "a": ("仕", "士"),
    "b": ("相", "象"),
    "n": ("傌", "馬", "马"),
    "r": ("俥", "車", "车"),
    "c": ("炮", "砲"),
    "p": ("兵", "卒"),
}
PIECE_CHI_DICT = {
    name: symbol for symbol, names in PIECE_DICT.items() for name in names
}
DIREC_DICT: Dict[int, Tuple[str, ...]] = {0: ("平",), 1: ("进", "上"), -1: ("退", "下")}
DIREC_CHI_DICT = {name: num for num, names in DIREC_DICT.items() for name in names}
COUNT2_DICT = {1: "前", 2: "后"}
COUNT2_CHI_DICT = {"前": 1, "后": 2}
COUNT3_DICT = {1: "前", 2: "中", 3: "后"}
COUNT345_DICT: Dict[int, Tuple[str, ...]] = {
    1: ("前",),
    2: ("二", "中"),
    3: ("三", "后"),
    4: ("四",),
    5: ("五",),
}
COUNT345_CHI_DICT = {
    name: num for num, names in COUNT345_DICT.items() for name in names
}


@dataclass
class Pos:
    x: int
    y: int

    def __eq__(self, other: "Pos") -> bool:
        return self.x == other.x and self.y == other.y

    def __str__(self) -> str:
        return self.ucci()

    def __hash__(self) -> int:
        return hash(self.ucci())

    def ucci(self) -> str:
        """转为 UCCI 格式的坐标"""
        return f"{chr(ord('a') + self.y)}{self.x}"

    def iccs(self) -> str:
        """转为 ICCS 格式的坐标"""
        return f"{chr(ord('A') + self.y)}{self.x}"

    def valid(self) -> bool:
        """判断坐标是否在范围内"""
        return 0 <= self.x <= 9 and 0 <= self.y <= 8


@dataclass
class Move:
    from_pos: Pos
    to_pos: Pos

    def __str__(self) -> str:
        return self.ucci()

    @classmethod
    def null(cls) -> "Move":
        """无移动"""
        return cls(Pos(0, 0), Pos(0, 0))

    def ucci(self) -> str:
        """转为 UCCI 格式的移动"""
        if self.from_pos == self.to_pos:
            return "0000"
        return f"{self.from_pos.ucci()}{self.to_pos.ucci()}"

    @classmethod
    def from_ucci(cls, ucci: str) -> "Move":
        """解析 UCCI 格式的移动"""
        if ucci == "0000":
            return cls.null()
        elif len(ucci) != 4:
            raise ValueError(f"UCCI字符串长度不符：{ucci}")
        else:
            ucci = ucci.lower()
            if not (cls.valid_coord(ucci[0:2]) and cls.valid_coord(ucci[2:4])):
                raise ValueError(f"UCCI字符串不合法：{ucci}")
            return cls(cls.parse_coord(ucci[0:2]), cls.parse_coord(ucci[2:4]))

    def iccs(self) -> str:
        """转为 ICCS 格式的移动"""
        return f"{self.from_pos.iccs()}-{self.to_pos.iccs()}"

    @classmethod
    def from_iccs(cls, iccs: str) -> "Move":
        """解析 ICCS 格式的移动"""
        if len(iccs) != 5 or iccs[2] != "-":
            raise ValueError(f"ICCS字符串不合法：{iccs}")
        else:
            iccs = iccs.lower()
            if not (cls.valid_coord(iccs[0:2]) and cls.valid_coord(iccs[3:5])):
                raise ValueError(f"ICCS字符串不合法：{iccs}")
            return cls(cls.parse_coord(iccs[0:2]), cls.parse_coord(iccs[3:5]))

    @staticmethod
    def valid_coord(coord: str) -> bool:
        return (
            len(coord) == 2
            and ord("a") <= ord(coord[0]) <= ord("i")
            and coord[1].isdigit()
            and 0 <= int(coord[1]) <= 9
        )

    @staticmethod
    def parse_coord(coord: str) -> Pos:
        return Pos(int(coord[1]), ord(coord[0]) - ord("a"))

    def chinese(self, board: "Board") -> str:
        """转为中文格式的移动"""

        piece = board.get_piece_at(self.from_pos)
        if not piece:
            raise ValueError(f"不合法的移动，起始位置没有棋子")
        piece_type = piece.piece_type

        diff_x = self.from_pos.x - self.to_pos.x
        if board.moveside:
            diff_x = -diff_x
        if diff_x == 0:
            direc = 0
        elif diff_x > 0:
            direc = 1
        else:
            direc = -1

        if direc != 0 and piece_type in (
            PieceType.KING,
            PieceType.CANNON,
            PieceType.ROOK,
            PieceType.PAWN,
        ):
            move_num = abs(diff_x)
        else:
            move_num = self.to_pos.y
            if board.moveside:
                move_num = 8 - move_num
            move_num += 1

        num_dict = NUM_CHI if board.moveside else NUM_DIGIT
        col_num = self.from_pos.y
        if board.moveside:
            col_num = 8 - col_num
        col_str = num_dict[col_num]

        """统计棋子在其纵线上的同种棋子的个数及第几个"""
        count = 1
        total_count = 0
        if board.moveside:
            start_x = self.from_pos.x + 1
            end_x = 10
        else:
            start_x = 0
            end_x = self.from_pos.x
        for pos in board.get_piece_pos(piece_type):
            if pos.y == self.from_pos.y:
                total_count += 1
                if start_x <= pos.x < end_x:
                    count += 1

        if total_count == 1:
            name = piece.name + col_str
        elif total_count == 2:
            name = COUNT2_DICT[count] + piece.name
        elif total_count == 3:
            name = COUNT3_DICT[count] + col_str
        else:
            name = COUNT345_DICT[count][0] + col_str

        return name + DIREC_DICT[direc][0] + num_dict[move_num - 1]

    @classmethod
    def from_chinese(cls, board: "Board", move_str: str) -> "Move":
        """解析中文格式的移动"""

        if len(move_str) != 4:
            raise ValueError(f"记谱字符串长度不符：{move_str}")

        def valid_piece(s: str) -> bool:
            return s in PIECE_CHI_DICT

        def parse_piece(s: str) -> PieceType:
            return PieceType(PIECE_CHI_DICT[s])

        def valid_num(s: str) -> bool:
            return s in NUM_CHI or s in NUM_DIGIT

        def parse_num(s: str) -> int:
            if s in NUM_CHI:
                return NUM_CHI.index(s) + 1
            if s in NUM_DIGIT:
                return NUM_DIGIT.index(s) + 1
            raise ValueError(f"记谱字符串中数字不合法：{s}")

        def valid_direc(s: str) -> bool:
            return s in DIREC_CHI_DICT

        def parse_direc(s: str) -> int:
            return DIREC_CHI_DICT[s]

        def valid_count2(s: str) -> bool:
            return s in COUNT2_CHI_DICT

        def parse_count2(s: str) -> int:
            return COUNT2_CHI_DICT[s]

        def valid_count345(s: str) -> bool:
            return s in COUNT345_CHI_DICT

        def parse_count345(s: str) -> int:
            return COUNT345_CHI_DICT[s]

        def find_piece(
            col: int, piece_type: PieceType, count: int = 1, min_count: int = 1
        ) -> Optional[Pos]:
            """找到某一纵线上第n个某种类型的棋子"""
            col -= 1
            if board.moveside:
                col = 8 - col
            col_pos = [pos for pos in board.get_piece_pos(piece_type) if pos.y == col]
            if len(col_pos) < min_count:
                return
            col_pos.sort(key=lambda p: p.x, reverse=board.moveside)
            return col_pos[count - 1]

        if (
            valid_piece(move_str[0])
            and valid_num(move_str[1])
            and valid_direc(move_str[2])
            and valid_num(move_str[3])
        ):
            """常规情况：
            第１字是棋子的名称。如“马”或“车”。
            第２字是棋子所在纵线的数字。
            第３字表示棋子移动的方向：横走用“平”，向前走用“进”或“上”，向后走用“退”或“下”。
            第４字是棋子进退的格数，或者到达纵线的数码。
            如：
            “炮二平五”，表示红炮从纵线二平移到纵线五
            “马８进７”，表示黑马从纵线８向前走到纵线７
            “车２退３”，表示黑车沿纵线２向后移动３格"""

            piece_type = parse_piece(move_str[0])
            col_num = parse_num(move_str[1])
            direc = parse_direc(move_str[2])
            move_num = parse_num(move_str[3])

            from_pos = find_piece(col_num, piece_type)

        elif (
            valid_count2(move_str[0])
            and valid_piece(move_str[1])
            and valid_direc(move_str[2])
            and valid_num(move_str[3])
        ):
            """当一方有２个名称相同的棋子位于同一纵线时，需要用“前”或“后”来加以区别：
            如：
            “前马退六”，表示前面的红马退到纵线六
            “后炮平４”，表示后面的黑炮平移到纵线４"""

            num = parse_count2(move_str[0])
            piece_type = parse_piece(move_str[1])
            direc = parse_direc(move_str[2])
            move_num = parse_num(move_str[3])

            if piece_type == PieceType.KING:
                raise ValueError(f"记谱字符串不合法：{move_str}")

            from_pos = None
            for col_num in range(1, 10):
                from_pos = find_piece(col_num, piece_type, num, 2)
                if from_pos:
                    break

        elif (
            valid_count345(move_str[0])
            and valid_num(move_str[1])
            and valid_direc(move_str[2])
            and valid_num(move_str[3])
        ):
            """当兵卒在同一纵线达到３个，用前中后区分，达到更多用前二三四五区分
            如：
            前兵九平八、二卒7平6
            此时可省略兵（卒），记做前九平八、二7平6，以达到都用4个汉字记谱的要求"""

            num = parse_count345(move_str[0])
            col_num = parse_num(move_str[1])
            direc = parse_direc(move_str[2])
            move_num = parse_num(move_str[3])
            piece_type = PieceType.PAWN

            from_pos = find_piece(col_num, piece_type, num, 3)

        else:
            raise ValueError(f"记谱字符串不合法：{move_str}")

        if not from_pos:
            raise ValueError(f"记谱字符串不合法：{move_str}，找不到对应的棋子")

        if direc == 0:
            to_x = from_pos.x
            move_num -= 1
            to_y = 8 - move_num if board.moveside else move_num
        else:
            if not board.moveside:
                direc = -direc
            if piece_type in (
                PieceType.KING,
                PieceType.CANNON,
                PieceType.ROOK,
                PieceType.PAWN,
            ):
                to_x = from_pos.x + move_num * direc
                to_y = from_pos.y
            else:
                move_num -= 1
                to_y = 8 - move_num if board.moveside else move_num
                diff_y = abs(from_pos.y - to_y)
                if piece_type == PieceType.BISHOP:
                    to_x = from_pos.x + 2 * direc
                elif piece_type == PieceType.ADVISOR:
                    to_x = from_pos.x + 1 * direc
                else:
                    diff_x = 2 if diff_y == 1 else 1
                    to_x = from_pos.x + diff_x * direc
        to_pos = Pos(to_x, to_y)

        if not (from_pos.valid() and to_pos.valid()):
            raise ValueError(f"移动方式非法：{move_str}，超出范围")
        return cls(from_pos, to_pos)
