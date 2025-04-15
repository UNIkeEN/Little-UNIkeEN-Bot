from enum import IntEnum
from typing import Any, List, Tuple, Union

from utils.basicEvent import *

NROWS = NCOLS = 17
class GoBangPiece(IntEnum):
    NOTHING = 0
    BLACK = 1
    WHITE = 2
    BLACKWHITE = 3
class GoBangDirection(IntEnum):
    UP = 0
    UPRIGHT = 1
    RIGHT = 2
    RIGHTDOWN = 3
    DOWN = 4
    DOWNLEFT = 5
    LEFT = 6
    LEFTUP = 7
def negativeDirection(direction: GoBangDirection):
    return (4 + direction) % 8
goBangMovement = [(-1, 0), (-1, 1), (0, 1), (1, 1,), (1, 0), (1, -1), (0, -1), (-1, -1)]
class GoBangGame():
    """五子棋逻辑"""
    def __init__(self):
        self.ROWS = NROWS
        self.COLS = NCOLS
        self.checkerboard = [[GoBangPiece.NOTHING for _ in range(self.COLS)] for _ in range(self.ROWS)]
        # buffer: [row, col, direction]: [piece, 黑棋在direction方向上有连续几颗棋子, 白棋在direction方向上有连续几颗棋子]
        self.buffer = [[[[GoBangPiece.NOTHING, 0, 0] for _ in range(8)] for _ in range(self.COLS)] for _ in range(self.ROWS)]
        self.pieceOrder = []
        self.currentPiece = GoBangPiece.BLACK
        self.doneFlag = False
    def _step(self, startPoint: Tuple, direction: GoBangDirection, dist:int=1):
        """从初始点向某方向行走dist格, 如果越界就返回None"""
        move = goBangMovement[direction]
        endPointX = startPoint[0] + move[0] * dist
        endPointY = startPoint[1] + move[1] * dist
        if endPointX < 0 or endPointX >= self.COLS:
            return None
        if endPointY < 0 or endPointY >= self.ROWS:
            return None
        return endPointX, endPointY

    def refresh(self):
        """更新游戏"""
        self.checkerboard = [[GoBangPiece.NOTHING for _ in range(self.COLS)] for _ in range(self.ROWS)]
        self.buffer = [[[[GoBangPiece.NOTHING, 0, 0] for _ in range(8)] for _ in range(self.COLS)] for _ in range(self.ROWS)]
        self.currentPiece = GoBangPiece.BLACK
        self.pieceOrder = []
        self.doneFlag = False

    def _checkFive(self, piece: GoBangPiece, pos: Tuple)->bool:
        """判断是否为 `五子连珠`"""
        bufferAtPos = self.buffer[pos[0]][pos[1]]
        for direction in range(4):
            anotherDirection = negativeDirection(direction)
            dist = bufferAtPos[direction][piece] + bufferAtPos[direction][piece]
            if dist == 4:
                return True
        return False

    def _checkChangLian(self, piece: GoBangPiece, pos: Tuple)->bool:
        """判断是否为 `长连`"""
        bufferAtPos = self.buffer[pos[0]][pos[1]]
        for direction in range(4):
            anotherDirection = negativeDirection(direction)
            dist = bufferAtPos[direction][piece] + bufferAtPos[direction][piece]
            if dist > 4:
                return True
        return False
    def _checkMian(self, piece: GoBangPiece, pos: Tuple) -> bool:
        """判断是否为 `眠n`"""
    def _checkDouble3(self, piece: GoBangPiece, pos: Tuple)->bool:
        """判断是否为 `双三`"""
        bufferAtPos = self.buffer[pos[0]][pos[1]]
        for dir1 in range(4):
            dir2 = negativeDirection(dir1)
            # TODO:
        return False
    def checkForbid(self, piece: GoBangPiece, pos: Tuple)->bool:
        """判断是否为 `禁手`"""
        if self._checkFive(piece, pos): return False
        if self._checkChangLian(piece, pos): return True
        if self._checkDouble3(piece, pos): return True
        return False
    def updateBuffer(self, pos: Tuple, piece: GoBangPiece):
        """更新缓存"""
        bufferAtPos = self.buffer[pos[0]][pos[1]]
        for direction in range(8):
            bufferAtPos[direction][0] = piece
            dist = bufferAtPos[direction][piece] + 1
            targetPos = self._step(pos, direction, dist)
            if targetPos == None: continue
            if self.checkerboard[targetPos[0]][targetPos[1]] != GoBangPiece.NOTHING:
                continue
            targetBuffer = self.buffer[targetPos[0]][targetPos[1]]
            targetLen = dist + bufferAtPos[negativeDirection(direction)][piece]
            targetBuffer[negativeDirection(direction)][piece] = targetLen
            if targetLen == 5:
                self.doneFlag = True
    def done(self)->bool:
        return self.doneFlag
    def act(self, pos: Tuple)->bool:
        """落子"""
        piece = self.currentPiece
        if self.checkerboard[pos[0]][pos[1]] != GoBangPiece.NOTHING:
            return False
        else:
            self.checkerboard[pos[0]][pos[1]] = piece
            self.pieceOrder.append(pos)
        self.updateBuffer(pos, piece)
        self.currentPiece = GoBangPiece.BLACKWHITE - self.currentPiece
        return True
    def getPieceLocs(self)->List:
        return self.pieceOrder[::2], self.pieceOrder[1::2]
def drawGoBangPIC(black, white, groupId=''):
    global NROWS, NCOLS
    COLOR_BLACK = (0, 0, 0, 255)
    COLOR_WHITE = (255, 255, 255, 255)
    COLOR_CHECKERBOARD = (245, 196, 124, 255)
    width = 720
    height = 1080
    img, draw, h = init_image_template('五子棋', width, height, (167,32,56,255))
    checkerboardSize = 600
    checkerboardDeltaRow = checkerboardSize / (NROWS-1)
    checkerboardDeltaCol = checkerboardSize / (NCOLS-1)
    checkerboardBase = ((width - checkerboardSize)//2, 300)
    # 棋盘底色
    draw.rectangle((0, checkerboardBase[1]-checkerboardBase[0],
                    width, checkerboardBase[1]+checkerboardSize+checkerboardBase[0]),
                    fill=COLOR_CHECKERBOARD)
    # 横着的线
    for i in range(NROWS):
        x0 = checkerboardBase[0]
        x1 = checkerboardBase[0]+checkerboardSize
        y  = checkerboardBase[1]+i*checkerboardDeltaRow
        draw.line((x0, y, x1, y), fill=COLOR_BLACK)
        txt = "%02d"%(NROWS-i)
        draw.text((x0-40, y-8), txt, fill=COLOR_BLACK,font=font_syhtmed_18)
    # 竖着的线
    for j in range(NCOLS):
        x  = checkerboardBase[0]+j*checkerboardDeltaCol
        y1 = checkerboardBase[1]
        y2 = checkerboardBase[1]+checkerboardSize
        draw.line((x, y1, x, y2), fill=COLOR_BLACK)
        txt = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[j]
        draw.text((x-5, y2+20), txt, fill=COLOR_BLACK,font=font_syhtmed_18)
    # 星
    def drawPiece(i, j, radius=checkerboardDeltaRow//2-5, color=COLOR_BLACK):
        # 下标从1开始
        i = NROWS - i
        j = j - 1
        xCenter = checkerboardBase[0]+j*checkerboardDeltaCol
        yCenter = checkerboardBase[1]+i*checkerboardDeltaRow
        draw.ellipse((xCenter-radius, yCenter-radius, xCenter+radius, yCenter+radius), fill=color, width=10)
    # 星
    drawPiece((NROWS+1)//2, (NCOLS+1)//2, 4)
    drawPiece(4, 4, 4)
    drawPiece(4, NCOLS+1-4, 4)
    drawPiece(NROWS+1-4, 4, 4)
    drawPiece(NROWS+1-4, NCOLS+1-4, 4)
    # 棋子
    for p in black:
        drawPiece(p[0]+1, p[1]+1, color=COLOR_BLACK)
    for p in white:
        drawPiece(p[0]+1, p[1]+1, color=COLOR_WHITE)
    save_path=(f'{SAVE_TMP_PATH}/gobang-{groupId}.png')
    img.save(save_path)
    return save_path
