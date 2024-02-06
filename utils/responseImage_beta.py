# 2023/12/24:ImageDraw.textsize，ImageFont.getsize 最新 Pillow 已弃用，已适配

import os
import requests
import base64
import re
import uuid
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from typing import Tuple, Union, Any

# 资源/临时路径
FONTS_PATH = 'resources/fonts'
SAVE_TMP_PATH = 'data/tmp'

# 字体预定义常量
FONT_SYHT_M42 = ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 42)
FONT_SYHT_M32 = ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 32)
FONT_SYHT_M28 = ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 28)
FONT_SYHT_M24 = ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 24)
FONT_SYHT_M18 = ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 18)
FONT_HYWH_36 = ImageFont.truetype(os.path.join(FONTS_PATH, '汉仪文黑.ttf'), 36)

# 颜色常量
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
PALETTE_GREY_BACK = (240, 240, 240, 255)
PALETTE_GREY_SUBTITLE = (95, 95, 95, 255)
PALETTE_GREY_CONTENT = (125, 125, 125, 255)

# 间距常量
'''
距离标准:
标准间隔:30 宽间隔:60
行间距: 11+ (txt_size[1])
'''
SPACE_NORMAL = 30
SPACE_DOUBLE = 60
SPACE_ROW = 12

class ResponseImage():
    def __init__(
        self,
        theme: str = 'unicorn', # 卡片主题风格
        autoSize: bool = True, # 自动调整大小
        layout: str = 'normal', # 布局(normal单栏/two-column双栏)
        height: int = 800,
        width: int = 880,
        title: str = '响应卡片', # 卡片标题
        titleColor = None, # 卡片标题栏颜色
        primaryColor: tuple = PALETTE_BLUE, # 主题色
        backColor: tuple = PALETTE_GREY_BACK, # 背景色
        footer: str = '',
        cardTitleFont: ImageFont.FreeTypeFont = FONT_SYHT_M32, # 前景卡片标题字体
        cardSubtitleFont: ImageFont.FreeTypeFont = FONT_SYHT_M24, # 前景卡片副标题字体
        cardBodyFont: ImageFont.FreeTypeFont = FONT_SYHT_M18 # 前景卡片内容字体
    ):
        self.theme = theme
        self.autoSize = autoSize
        self.layout = layout
        if not self.autoSize:
            self.height, self.width = height, width
        else:
            self.height, self.width = 0, width # 支持指定width自动调整高度
        self.title = title
        self.titleColor = titleColor if titleColor!=None else primaryColor
        self.primaryColor = primaryColor
        self.backColor = backColor
        self.footer = footer
        self.cardList = [] # 前景卡片列表
        self.cardTitleFont = cardTitleFont
        self.cardSubtitleFont = cardSubtitleFont
        self.cardBodyFont = cardBodyFont
        self.columnSep = 0 # 双栏分隔处卡片序号
        self.blankList = []
        self.img, self.draw = None, None
        if not os.path.exists(SAVE_TMP_PATH):
            os.mkdir(SAVE_TMP_PATH)

    # 预定义卡片类型
    class Card():
        def __init__(self, style, params):
            data = {'style': style}
            for key, value in params.items():
                if key not in ['self', '__class__'] and value!=None:
                    data[key] = value
            self.data = data
    class BlankCard(Card):
        '''空白类型卡片, 参数如下: 
        size: 卡片高度
        backColor: 卡片背景色 (可选, 默认为白色)'''
        def __init__(
            self,
            size:int = 0,
            backColor:tuple =None
        ):
            params = vars()
            super().__init__('blank', params)
    class NormalCard(Card):
        '''普通类型卡片, 参数如下: 
        title: 标题 (可选)
        subtitle: 副标题 (可选)
        keyword: 关键句 (可选, 将以主色显示)
        body: 正文 (可选)
        icon: 图标 (可选, 支持本地/网络图片url, base64编码, Image对象)
        titleFontColor: 标题字体颜色 (可选, 默认为黑)
        subtitleFontColor: 副标题字体颜色 (可选, 默认为深灰)
        bodyFontColor: 正文字体颜色 (可选, 默认为灰)
        backColor: 卡片背景色 (可选, 默认为白色)'''
        def __init__(
            self,
            title:str = None,
            subtitle:str = None,
            keyword:str = None,
            body:str = None,
            icon = None,
            titleFontColor: tuple = None,
            subtitleFontColor: tuple = None,
            bodyFontColor: tuple = None,
            backColor:tuple =None
        ):
            params = vars()
            super().__init__('normal', params)
    class NoticeCard(Card):
        '''通知类型卡片, 参数如下: 
        title: 标题 (可选)
        subtitle: 副标题 (可选)
        keyword: 关键句 (可选, 将以主色显示)
        body: 正文 (可选)
        illustration: 配图 (可选, 支持本地/网络图片url, base64编码, Image对象)
        titleFontColor: 标题字体颜色 (可选, 默认为黑)
        subtitleFontColor: 副标题字体颜色 (可选, 默认为深灰)
        bodyFontColor: 正文字体颜色 (可选, 默认为灰)
        backColor: 卡片背景色 (可选, 默认为白色)'''
        def __init__(
            self,
            title:str = None,
            subtitle:str = None,
            keyword:str = None,
            body:str = None,
            illustration = None,
            titleFontColor: tuple = None,
            subtitleFontColor: tuple = None,
            bodyFontColor: tuple = None,
            backColor:tuple =None
        ):
            params = vars()
            super().__init__('notice', params)
    class RichContentCard(Card):
        '''复合类型卡片, 参数如下: 
        raw_content: 内容 (可选, 列表嵌套元组)
        icon: 图标 (可选, 支持本地/网络图片url, base64编码, Image对象)
        titleFontColor: 标题字体颜色 (可选, 默认为黑)
        subtitleFontColor: 副标题字体颜色 (可选, 默认为深灰)
        bodyFontColor: 正文字体颜色 (可选, 默认为灰)
        backColor: 卡片背景色 (可选, 默认为白色)'''
        def __init__(
            self,
            raw_content:list = None,
            icon = None,
            titleFontColor: tuple = None,
            subtitleFontColor: tuple = None,
            bodyFontColor: tuple = None,
            backColor:tuple =None
        ):
            params = vars()
            super().__init__('rich-content', params)

    # 画圆角矩形
    def drawRoundedRectangle(self, x1, y1, x2, y2, fill, r = 8, border=False, borderColor = PALETTE_GREY_BORDER, borderWidth = 1, target = None): 
        if target == None:
            draw = self.draw
        else:
            draw = ImageDraw.Draw(target)
        draw.ellipse((x1, y1, x1+2*r, y1+2*r), fill = fill)
        draw.ellipse((x2-2*r, y1, x2, y1+2*r), fill = fill)
        draw.ellipse((x1, y2-2*r, x1+2*r, y2), fill = fill)
        draw.ellipse((x2-2*r, y2-2*r, x2, y2), fill = fill)
        draw.rectangle((x1+r, y1, x2-r, y2), fill = fill)
        draw.rectangle((x1, y1+r, x2, y2-r),fill = fill)
        if border:
            draw.arc((x1, y1, x1+2*r, y1+2*r), 180, 270, borderColor, borderWidth)
            draw.arc((x2-2*r, y1, x2, y1+2*r), 270, 360, borderColor, borderWidth)
            draw.arc((x1, y2-2*r, x1+2*r, y2), 90, 180, borderColor, borderWidth)
            draw.arc((x2-2*r, y2-2*r, x2, y2), 0, 90, borderColor, borderWidth)
            draw.line((x1, y1+r, x1, y2-r), borderColor, borderWidth)
            draw.line((x2, y1+r, x2, y2-r), borderColor, borderWidth)
            draw.line((x1+r, y1, x2-r, y1), borderColor, borderWidth)
            draw.line((x1+r, y2, x2-r, y2), borderColor, borderWidth)
        return target

    # 增加卡片 (允许使用Card类或字典形式输入)
    def addCard(self, card):
        if isinstance(card, self.Card):
            self.cardList.append(card.data)
        elif isinstance(card, dict):
            self.cardList.append(card)

    def addCardList(self, clist):
        for card in clist:
            self.addCard(card)
    
    # autoSize计算高度
    def calcHeight(self):
        width, height = self.width, 0
        cardList = self.cardList
        txt_size = get_font_size(self.title, FONT_HYWH_36)
        height += txt_size[1]+115 # 加标题距离
        txt_size_18 = get_font_size('测试', FONT_SYHT_M18)
        height += (2*txt_size_18[1]+SPACE_NORMAL+SPACE_ROW if self.footer!='' else txt_size_18[1]+SPACE_NORMAL) + 15 # 加页脚距离
        if self.layout=='two-column' and len(self.cardList)>1:
            w_card = (width - 2*SPACE_DOUBLE - SPACE_NORMAL) / 2
        else:
            self.layout = 'normal'
            w_card = width - 2*SPACE_DOUBLE
        for i in range(len(cardList)):
            h_card = 2*SPACE_NORMAL-SPACE_ROW
            if cardList[i]['style'] in ['blank']:
                if cardList[i].get('size') != None and cardList[i]['size']>= -SPACE_NORMAL:
                    h_card = cardList[i]['size']+2*SPACE_NORMAL
                    cardList[i]['height'] = h_card + SPACE_NORMAL

            elif cardList[i]['style'] in ['normal', 'notice']:
                if cardList[i]['style']=='normal':
                    txtWidthLimit = w_card - 2*SPACE_NORMAL- 8 - (0 if cardList[i].get('icon') == None else SPACE_NORMAL+90)    
                else:
                    txtWidthLimit = w_card - 2*SPACE_NORMAL
                    if cardList[i].get('illustration') != None:
                        image = self.openImage(cardList[i]['illustration'])
                        if image.width > w_card - 2*SPACE_NORMAL:
                            h_card += int(image.height * (w_card - 2*SPACE_NORMAL) / image.width)
                            h_card += SPACE_ROW
                        else:
                            h_card += image.height
                            h_card += SPACE_ROW
                cardList[i]['content']=[]
                titleColor = PALETTE_BLACK if cardList[i].get('titleFontColor') == None else cardList[i]['titleFontColor']
                subtitleColor = PALETTE_GREY_SUBTITLE if cardList[i].get('subtitleFontColor') == None else cardList[i]['subtitleFontColor']
                bodyColor = PALETTE_GREY_SUBTITLE if cardList[i].get('bodyFontColor') == None else cardList[i]['bodyFontColor']
                if cardList[i].get('title') != None:
                    parsed, h = self.parseLine(cardList[i]['title'], self.cardTitleFont, txtWidthLimit)
                    cardList[i]['content'].extend([('title', t, titleColor) for t in parsed])
                    h_card += h
                if cardList[i].get('subtitle') != None:
                    parsed, h = self.parseLine(cardList[i]['subtitle'], self.cardSubtitleFont, txtWidthLimit)
                    cardList[i]['content'].extend([('subtitle', t, subtitleColor) for t in parsed])
                    h_card += h
                if cardList[i].get('keyword') != None:
                    parsed, h = self.parseLine(cardList[i]['keyword'], self.cardSubtitleFont, txtWidthLimit)
                    cardList[i]['content'].extend([('keyword', t, self.primaryColor) for t in parsed])
                    h_card += h
                if cardList[i].get('body') != None:
                    parsed, h = self.parseLine(cardList[i]['body'], self.cardBodyFont, txtWidthLimit)
                    cardList[i]['content'].extend([('body', t, bodyColor) for t in parsed])
                    h_card += h
                if (cardList[i].get('icon') != None) and h_card <= (2*SPACE_NORMAL+90):
                    h_card = 2*SPACE_NORMAL+90

            elif cardList[i]['style'] in ['rich-content']:
                txtWidthLimit = w_card - 2*SPACE_NORMAL - 8 - (0 if cardList[i].get('icon') == None else SPACE_NORMAL+90) 
                cardList[i]['content']=[]
                if cardList[i].get('raw_content') != None:
                    for cnt in cardList[i]['raw_content']:
                        if cnt[0]=='separator':
                            h_card += 3*SPACE_ROW+1
                            cardList[i]['content'].extend([(cnt[0],)])
                            continue
                        if cnt[0]=='progressBar':
                            h_card += 4*SPACE_ROW
                            cardList[i]['content'].append(cnt)
                            continue
                        if cnt[0]=='illustration':
                            image = self.openImage(cnt[1])
                            if image.width > txtWidthLimit:
                                h_card += int(image.height * (txtWidthLimit) / image.width)
                                h_card += SPACE_ROW
                            else:
                                h_card += image.height
                                h_card += SPACE_ROW
                            cardList[i]['content'].append(cnt)
                            continue
                        if cnt[0]=='title':
                            font = self.cardTitleFont
                            color = PALETTE_BLACK if len(cnt)<=2 else cnt[2]
                        elif cnt[0]=='subtitle':
                            font = self.cardSubtitleFont
                            color = PALETTE_GREY_SUBTITLE if len(cnt)<=2 else cnt[2]
                        elif cnt[0]=='keyword':
                            font = self.cardSubtitleFont
                            color = self.primaryColor
                        elif cnt[0]=='body':
                            font = self.cardBodyFont
                            color = PALETTE_GREY_CONTENT if len(cnt)<=2 else cnt[2]
                        parsed, h = self.parseLine(cnt[1], font, txtWidthLimit)
                        cardList[i]['content'].extend([(cnt[0], t, color) for t in parsed])
                        h_card += h
                if (cardList[i].get('icon') != None) and h_card <= (2*SPACE_NORMAL+90):
                    h_card = 2*SPACE_NORMAL+90
                
            cardList[i]['height'] = h_card + SPACE_NORMAL
            cardList[i]['width'] = w_card
        cardTotHeight = 0
        for i in range(len(cardList)):
            cardTotHeight += cardList[i]['height']
        if self.autoSize and self.layout=='normal':
            self.height = height + cardTotHeight
        elif self.layout=='two-column':
            t, min = 0, cardTotHeight
            for i in range(len(cardList)):
                t += cardList[i]['height']
                # print(i, ' ', abs(cardTotHeight - 2*t))
                if abs(cardTotHeight - 2*t) <= min:
                    min = abs(cardTotHeight - 2*t)
                else:
                    self.columnSep = i - 1
                    t = t - cardList[i]['height']
                    if self.autoSize:
                        self.height = height + max(t, cardTotHeight-t)
                    break
        self.cardList = cardList

    # 分行
    def parseLine(self, raw_txt, font, widthLimit):
        txt_parse = []
        txt_line = ""
        height = 0
        for word in raw_txt:
            if len(txt_parse)>0 and txt_line=="" and word in ['，','；','。','、','"','：','.','”',')','）']: #避免标点符号在首位
                txt_parse[-1]+=word
                continue
            txt_line+=word
            if get_font_size(txt_line, font)[0]>widthLimit:
                txt_parse.append(txt_line)
                txt_line=""
            if word=='\n':
                if txt_line=='\n':
                    txt_parse.append(' ')
                else:
                    txt_parse.append(txt_line[:-1])
                txt_line=""
                continue
        if txt_line!="":
            txt_parse.append(txt_line)
        if len(txt_parse)==0:
            txt_parse=[' ']
        height = sum([SPACE_ROW + get_font_size(txt, font)[1] for txt in txt_parse]) 
        # height=len(txt_parse)*(font.getsize('测试')[1]+SPACE_ROW)
        # print(txt_parse)
        return txt_parse, height

    # 解码 base64
    def decodeBase64(self, src):
        # 1、信息提取
        result = re.search("data:image/(?P<ext>.*?);base64,(?P<data>.*)", src, re.DOTALL)
        if result:
            ext = result.groupdict().get("ext")
            data = result.groupdict().get("data")
        else:
            raise Exception("Do not parse!")
        # 2、base64解码
        img = base64.urlsafe_b64decode(data)
        # 3、二进制文件保存
        filename = "{}/{}.{}".format(SAVE_TMP_PATH,uuid.uuid4(), ext)
        with open(filename, "wb") as f:
            f.write(img)
        return filename

    # 处理图像链接
    def openImage(self, url):
        if isinstance(url, Image.Image): # 传入已经画好的图片对象
            return url
        if isinstance(url, BytesIO):
            return Image.open(url)
        if isinstance(url, str):
            if url[:4]=="data": # 传入图片地址
                img_ = Image.open(self.decodeBase64(url))
            elif url[:4]=="http":
                url_ = requests.get(url)
                img_ = Image.open(BytesIO(url_.content))
            else:
                try:
                    img_ = Image.open(url)
                except BaseException as e:
                    raise RuntimeError('unknow url str: {}'.format(url))
            return img_
        raise RuntimeError('unknow url format')

    # 绘制
    def drawImage(self):
        # 绘制背景
        width, height = self.width, self.height
        self.img = Image.new('RGBA', (width, height), self.backColor)
        self.draw = ImageDraw.Draw(self.img)
        draw = self.draw
        # 绘制标题
        txt_size = get_font_size(self.title, FONT_HYWH_36) 
        self.drawRoundedRectangle(x1=width/2-txt_size[0]/2-15, y1=40, x2=width/2+txt_size[0]/2+15,y2=txt_size[1]+70, fill=self.titleColor)
        draw.text((width/2-txt_size[0]/2,55), self.title, fill=PALETTE_WHITE, font=FONT_HYWH_36)
        top = txt_size[1]+115
        top_0 = top
        # 绘制页脚
        txt_size = get_font_size('Powered By Little-UNIkeEN-Bot', FONT_SYHT_M18)
        draw.text((width/2-txt_size[0]/2, height-SPACE_NORMAL-txt_size[1]), 'Powered By Little-UNIkeEN-Bot', fill=PALETTE_GREY_CONTENT, font = FONT_SYHT_M18)
        if self.footer!='':
            txt_size = get_font_size(self.footer, FONT_SYHT_M18)
            draw.text((width/2-txt_size[0]/2, height-SPACE_NORMAL-SPACE_ROW-2*txt_size[1]), self.footer, fill=PALETTE_GREY_CONTENT, font = FONT_SYHT_M18)
        # 绘制卡片
        i=0
        for card in self.cardList:
            if self.layout == 'normal':
                cardLeft = SPACE_DOUBLE
                cardRight = width-SPACE_DOUBLE
            elif self.layout == 'two-column':
                cardLeft = SPACE_DOUBLE if i <= self.columnSep else (SPACE_DOUBLE + SPACE_NORMAL +card['width'])
                cardRight = SPACE_DOUBLE+card['width'] if i <= self.columnSep else (width - SPACE_DOUBLE)
                if i == self.columnSep+1:
                    top = top_0
                i+=1
            y_top = top
            backColor = PALETTE_WHITE if card.get('backColor') == None else card['backColor']
            if card['style']=='blank':
                self.drawRoundedRectangle(x1=cardLeft, y1=top, x2=cardRight, y2=top+card['height']-SPACE_NORMAL, fill=backColor, border = True)
                top += card['height']
                self.blankList.append((cardLeft, top, cardRight, top+card['height']-SPACE_NORMAL))
                continue
            self.drawRoundedRectangle(x1=cardLeft, y1=top, x2=cardRight, y2=top+card['height']-SPACE_NORMAL, fill=backColor, border = True)
            y_top += SPACE_NORMAL
            x_left = cardLeft + SPACE_NORMAL
            if card['style'] in ['normal', 'rich-content'] and card.get('icon') != None :
                img_icon = (self.openImage(card['icon'])).resize((90,90))
                self.img.paste(img_icon, (int(x_left), y_top))
                x_left += (90+SPACE_NORMAL)
            titleColor = PALETTE_BLACK if card.get('titleFontColor') == None else card['titleFontColor']
            subtitleColor = PALETTE_GREY_SUBTITLE if card.get('subtitleFontColor') == None else card['subtitleFontColor']
            bodyColor = PALETTE_GREY_SUBTITLE if card.get('bodyFontColor') == None else card['bodyFontColor']
            if card.get('content') != None:
                for line in card['content']:
                    if line[0]=='separator':
                        x_l = x_left
                        y_top += SPACE_ROW
                        draw.line((x_l, y_top, cardRight-SPACE_NORMAL, y_top), PALETTE_GREY_BORDER, 1)
                        y_top += (2*SPACE_ROW+1)
                        continue
                    if line[0] in ['progressBar']:
                        x_l = x_left
                        y_top += SPACE_ROW
                        x_r = cardRight-SPACE_NORMAL
                        clrfront = PALETTE_GREEN
                        clrback = PALETTE_LIGHTGREEN
                        if len(line)==4:
                            clrfront = line[2]
                            clrback = line[3]
                        if len(line)==3 and line[2]=='auto':
                            if line[1]>=0.6:
                                clrfront = PALETTE_ORANGE
                                clrback = PALETTE_LIGHTORANGE
                            if line[1]>=0.9:
                                clrfront = PALETTE_RED
                                clrback = PALETTE_LIGHTRED
                        self.drawRoundedRectangle(x_l, y_top, x_r, y_top+SPACE_ROW, fill=clrback, r=3.5)
                        if line[1]>0:
                            self.drawRoundedRectangle(x_l, y_top, x_l+(x_r-x_l)*(line[1] if line[1]>=0.01 else 0.01), y_top+SPACE_ROW, fill=clrfront, r=3.5)
                        y_top += (3*SPACE_ROW)
                        continue
                    if line[0] in ['illustration']:
                        illu = self.openImage(line[1])
                        # print(line[1])
                        if illu.width > card['width'] - 2*(SPACE_NORMAL):
                            illu = illu.resize((int(card['width'] - 2*SPACE_NORMAL), int(illu.height * (card['width'] - 2*SPACE_NORMAL) / illu.width)))
                        self.img.paste(illu, (int(cardLeft+(card['width']-illu.width)/2), y_top))
                        y_top += (illu.height+SPACE_ROW)
                        continue
                    if line[0]=='title':
                        font = self.cardTitleFont
                    elif line[0]=='subtitle':
                        font = self.cardSubtitleFont
                    elif line[0]=='keyword':
                        font = self.cardSubtitleFont
                    elif line[0]=='body':
                        font = self.cardBodyFont
                    txt_size=get_font_size(line[1], font)
                    x_l = cardLeft+(card['width']-txt_size[0])/2 if card['style']=='notice' else x_left
                    draw.text((x_l, y_top), line[1], fill=line[2], font = font)
                    y_top += (txt_size[1]+SPACE_ROW) 
            
            if card['style']=='notice' and card.get('illustration') != None:
                illu = self.openImage(card['illustration'])
                if illu.width > card['width'] - 2*(SPACE_NORMAL):
                    illu = illu.resize((int(card['width'] - 2*SPACE_NORMAL), int(illu.height * (card['width'] - 2*SPACE_NORMAL) / illu.width)))
                self.img.paste(illu, (int(cardLeft+(card['width']-illu.width)/2), y_top))
                y_top += (illu.height+SPACE_ROW)
            top += card['height']

    def generateImage(self, savePath = None):
        '''生成图片:
        参数: savePath 为保存路径
        返回值: 绘制完成的 Image 对象'''
        self.calcHeight()
        self.drawImage()
        if savePath!=None:
            self.img.save(savePath)
        return self.img.copy()
        
    def getBlankCoord(self):
        return self.blankList
        
class CardDrawError(Exception):
    def __init__(self,errorInfo):
        super().__init__(self)
        self.errorInfo = errorInfo
    def __str__(self):
        return self.errorInfo


# -----------------
# 基于 Pillow 的辅助工具函数
    
def get_font_size(text:str, 
                  font:ImageFont.FreeTypeFont)->Tuple[int,int]:
    text_bbox = font.getbbox(text)
    text_width, text_height = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1] + 0.1 * font.size  # bbox不一定完全包含文字
    return (int(text_width), int(text_height))


def draw_gradient_rectangle(img:Image.Image, 
                            position:Tuple[int,int,int,int], 
                            fill:Union[Tuple[Any,Any],Tuple[Any,Any,Any,Any]]):
    """
    在图像上绘制渐变色矩形。

    参数:
    img: PIL Image对象，要绘制渐变矩形的图像。
    position: 矩形的位置，格式为(x1, y1, x2, y2)的坐标元组。
    fill: 渐变色填充，是RGBA颜色元组的列表。如果列表包含两个元组，则创建从左至右的线性渐变；
          如果包含四个元组，则分别代表左上、右上、左下、右下角的颜色，用于创建双线性渐变。

    当渐变参数不等于2或4时，抛出异常。
    """
    if len(fill) != 2 and len(fill) != 4:
        raise ValueError("Fill parameter must contain either 2 or 4 color tuples.")

    x1, y1, x2, y2 = position
    width, height = x2 - x1, y2 - y1
    canvas = Image.new('RGBA', (width, height), "white")

    if len(fill) == 2:
        # 线性渐变
        color_start, color_end = fill
        for x in range(width):
            gradient_color = tuple(
                int(color_start[i] + (float(x) / width) * (color_end[i] - color_start[i])) for i in range(4)
            )
            for y in range(height):
                canvas.putpixel((x, y), gradient_color)

    elif len(fill) == 4:
        # 双线性渐变
        top_left, top_right, bottom_left, bottom_right = fill
        for x in range(width):
            for y in range(height):
                horizontal_ratio = float(x) / width
                vertical_ratio = float(y) / height

                tmp1 = tuple(
                    int(top_left[i] + horizontal_ratio * (top_right[i] - top_left[i])) for i in range(4)
                )
                tmp2 = tuple(
                    int(bottom_left[i] + horizontal_ratio * (bottom_right[i] - bottom_left[i])) for i in range(4)
                )
                gradient_color = tuple(
                    int(tmp1[i] + vertical_ratio * (tmp2[i] - tmp1[i])) for i in range(4)
                )
                canvas.putpixel((x, y), gradient_color)

    img.paste(canvas, position)

def draw_gradient_text(img:Image.Image,
                       position:Tuple[int,int],
                       text:str,
                       fill:Union[Tuple[Any,Any],Tuple[Any,Any,Any,Any]],
                       font:ImageFont.FreeTypeFont):
    """
    在图像上绘制渐变色填充的文本。

    参数:
    img: PIL Image对象，要绘制文本的图像。
    position: 文本的位置，格式为(x, y)的坐标元组。
    text: 要绘制的文本。
    fill: 渐变色填充，同draw_gradient_rectangle函数。
    font: PIL ImageFont对象，定义文本的字体。

    当渐变参数不等于2或4时，抛出异常。
    """
    if len(fill) != 2 and len(fill) != 4:
        raise ValueError("Fill parameter must contain either 2 or 4 color tuples.")

    # 为反锯齿创建更大的字体，缩放系数大于2较影响性能
    scale_factor = 2
    font_scaled = ImageFont.truetype(font.path, font.size * scale_factor)
    text_width, text_height = get_font_size(text, font_scaled)

    gradient_img = Image.new('RGBA', (text_width, text_height), (0, 0, 0, 0))
    draw_gradient_rectangle(gradient_img, (0, 0, text_width, text_height), fill)

    text_img = Image.new('RGBA', (text_width, text_height), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_img)
    text_draw.text((0, 0), text, fill=(255, 255, 255, 255), font=font_scaled)

    gradient_text_img = Image.new('RGBA', (text_width, text_height), (0, 0, 0, 0))
    gradient_pixels = gradient_img.load()
    text_pixels = text_img.load()
    for y in range(text_height):
        for x in range(text_width):
            if text_pixels[x, y][3] > 0:
                gradient_text_img.putpixel((x, y), gradient_pixels[x, y])

    gradient_text_img = gradient_text_img.resize((text_width // scale_factor, text_height // scale_factor), Image.Resampling.LANCZOS)

    img.paste(gradient_text_img, position, gradient_text_img)