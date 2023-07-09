from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:
    from .board import Board

img_dir = Path(__file__).parent / "resources" / "images"


def draw_board(board: "Board", sameside: bool = True) -> BytesIO:
    pieces = board._board
    side = board.moveside if sameside else not board.moveside
    bg_name = "board_red.png" if side else "board_black.png"
    bg = Image.open(img_dir / bg_name)
    mark = Image.open(img_dir / "mark.png")

    last_move = board.last_move
    from_pos = last_move.from_pos
    to_pos = last_move.to_pos
    draw_mark = True
    if from_pos == to_pos:
        draw_mark = False

    for i, line in enumerate(pieces):
        for j, piece in enumerate(line):

            if side:
                x = 200 + 300 * j
                y = 3150 - 300 * i
            else:
                x = 2600 - 300 * j
                y = 450 + 300 * i

            if draw_mark and (
                (i == from_pos.x and j == from_pos.y)
                or (i == to_pos.x and j == to_pos.y)
            ):
                bg.paste(mark, (x, y), mask=mark)

            if not piece:
                continue

            img_name = piece.symbol.lower() + ("_red" if piece.color else "_black")
            img = Image.open(img_dir / f"{img_name}.png")
            bg.paste(img, (x, y), mask=img)

    output = BytesIO()
    bg = bg.convert("RGBA").resize((775, 975), Image.ANTIALIAS)
    bg.save(output, format="png")
    return output
