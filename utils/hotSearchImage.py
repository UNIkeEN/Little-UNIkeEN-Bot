import enum
from PIL import Image, ImageDraw, ImageFont
import os, os.path
from typing import Tuple, List, Dict, Any, Union
FONTS_PATH = 'resources/fonts'
SAVE_TMP_PATH = 'data/tmp'

class Fonts(enum.EnumMeta):
    FONT_SYHT_M42 = ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 42)
    FONT_SYHT_M32 = ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 32)
    FONT_SYHT_M24 = ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 24)
    FONT_SYHT_M18 = ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 18)
    FONT_HYWH_36 = ImageFont.truetype(os.path.join(FONTS_PATH, '汉仪文黑.ttf'), 36)

class Colors(enum.EnumMeta):
    PALETTE_SJTU_RED = (200, 22, 30, 255)
    PALETTE_SJTU_DARKRED = (167, 32, 56, 255)
    PALETTE_SJTU_ORANGE = (240, 131, 0, 255)
    PALETTE_SJTU_YELLOW = (253, 208, 0, 255)
    PALETTE_SJTU_BLUE = (0, 134, 209, 255)
    PALETTE_SJTU_DARKBLUE = (0, 64, 152, 255)
    PALETTE_SJTU_GREEN = (51, 141, 39, 255)
    PALETTE_SJTU_CYAN = (0, 81, 78, 255)

    PALETTE_BLACK = (0, 0, 0, 255)
    PALETTE_WHITE = (255, 255, 255, 255)
    PALETTE_GREY = (158, 158, 158, 255)
    PALETTE_RED = (221, 0, 38, 255)
    PALETTE_LIGHTRED = (255, 232, 236, 255)
    PALETTE_GREEN = (0, 191, 48, 255)
    PALETTE_LIGHTGREEN = (219, 255, 228, 255)
    PALETTE_ORANGE = (244, 149, 4, 255)
    PALETTE_LIGHTORANGE = (254, 232, 199, 255)
    PALETTE_BLUE = (32, 131, 197, 255)
    PALETTE_LIGHTBLUE = (9, 188, 211, 255)
    PALETTE_CYAN = (0, 150, 136, 255)     
    PALETTE_INDIGO = (69, 84, 164, 255)

    PALETTE_GREY_BORDER = (213, 213, 213, 255)
    PALETTE_GERY_BACK = (240, 240, 240, 255)
    PALETTE_GREY_SUBTITLE = (95, 95, 95, 255)
    PALETTE_GREY_CONTENT = (125, 125, 125, 255)

class HotSearchUnit():
    """"""
    def __init__(self, 
                 text:str,
                 color:Colors, 
                 font:Fonts,
                 width:int,
                 index:int) -> None:
        self.text = text
        self.color = color
        self.font = font
        self.width = width
        self.index = index
        self.marginLeft = 80
        self.numMarginLeft = 30
        self.marginRight = 10
        self.marginUp = 10
        self.marginDown = 10
        self.rowSpacing = 10
        self._splitedText = None
        self._calcedHeight = None

    def parseLine(self)->List[str]:
        if self._splitedText != None:
            return self._splitedText
        lineWidth = self.width - self.marginLeft - self.marginRight
        if lineWidth < 100:
            raise RuntimeError('line width too narrow')
        result:List[str] = []
        res = self.text
        def parseOneLine(txt:str, targetWidth:int)->Tuple[str, str]:
            lh, rh = 0, len(txt)
            while lh < rh:
                mid = (lh+rh+1)>>1
                res = txt[0:mid]
                if self.font.getsize(res)[0] < targetWidth:
                    lh = mid
                else:
                    rh = mid - 1
            return txt[:lh], txt[lh:]
        while len(res) > 0:
            text, res = parseOneLine(res, lineWidth)
            result.append(text)
        self._splitedText = result
        return result
            
    def calcHeight(self)->int:
        if self._calcedHeight != None:
            return self._calcedHeight
        tmp = self.parseLine()
        height = self.marginUp + self.marginDown
        height += (len(tmp) - 1) * self.rowSpacing
        height += sum([self.font.getsize(line)[1] for line in tmp])
        self._calcedHeight = height
        return height
    
    def draw(self, draw:ImageDraw.ImageDraw, startPos:Tuple[int, int])->None:
        indexPos = (startPos[0] + self.numMarginLeft, startPos[1] + self.marginUp)
        indexPosA = (indexPos[0]-2 , indexPos[1]-2)
        indexPosB = (indexPosA[0]+31, indexPosA[1]+31)
        draw.rounded_rectangle((indexPosA, indexPosB), radius=3, 
                               fill=Colors.PALETTE_RED if self.index <= 10 else Colors.PALETTE_GREY)
        if self.index < 10:
            indexPos = (indexPos[0]+7, indexPos[1])
        draw.text(indexPos, str(self.index), fill=self.color, font=self.font)
        currentPos = (startPos[0] + self.marginLeft, startPos[1] + self.marginUp)
        for txt in self.parseLine():
            draw.text(currentPos, txt, fill=self.color, font=self.font)
            currentPos = (currentPos[0], currentPos[1]+self.rowSpacing+self.font.getsize(txt)[1])

class HotSearchImage():
    def __init__(self, 
                 meta:List[Dict[str, Any]],
                 width:int,
                 defaultColor:Colors,
                 defaultFont:Fonts,
                 bgColor:Colors) -> None:
        """
        @meta: List[
            {
                "text": str,
                "color": Union[None, Colors],
                "font": Union[None, Fonts],
            }
        ]
        """
        self.width = width
        self.unit:List[HotSearchUnit] = [HotSearchUnit(
            m['text'],
            m['color'] if 'color' in m.keys() else defaultColor,
            m['font'] if 'font' in m.keys() else defaultFont,
            width,
            index+1
        ) for index, m in enumerate(meta)]
        self.bgColor = bgColor
        self.marginUp = 50
        self.marginDown = 50
    def calcHeight(self,):
        height = self.marginUp + self.marginDown
        height += sum([u.calcHeight() for u in self.unit])
        return height
    def draw(self)->Image.Image:
        height = self.calcHeight()
        img = Image.new('RGB', (self.width, height), self.bgColor)
        draw = ImageDraw.Draw(img)
        h = self.marginUp
        for u in self.unit:
            u.draw(draw, (0, h))
            h += u.calcHeight()
        return img