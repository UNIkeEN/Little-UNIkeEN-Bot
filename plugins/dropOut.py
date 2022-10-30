from typing import Union, Any
from utils.basicEvent import *
from utils.basicConfigs import *
from utils.responseImage import FONT_SYHT_M32
from utils.standardPlugin import StandardPlugin
from PIL import Image, ImageDraw, ImageFont
import os.path
import re
from datetime import date, timedelta

FONT_FZXBS = ImageFont.truetype(os.path.join(FONTS_PATH, '方正小标宋.ttf'), 68)
FONT_SYST = ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSerifCN-Bold.otf'), 62)
FONT_SYHT_M36 = ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 36)

class DropOut(StandardPlugin):
    def __init__(self) -> None:
        self.pattern = re.compile(r'^(.{1,8})退学$')
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return self.pattern.match(msg) != None
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        name = self.pattern.findall(msg)[0]
        dropoutDate = date.today() + timedelta(days=7)
        picPath = drawDropout(name, data['user_id'], dropoutDate)
        picPath = picPath if os.path.isabs(picPath) else os.path.join(ROOT_PATH, picPath)
        send(target, f'[CQ:image,file=files://{picPath}]', data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'DropOut',
            'description': '一键退学',
            'commandDescription': 'xxx退学',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.2',
            'author': 'Unicorn',
        }
def genChineseDate(d: date)->str:
    chineseDigitDict = {
        '1': '一', '2': '二', '3': '三',
        '4': '四', '5': '五', '6': '六',
        '7': '七', '8': '八', '9': '九', '0': '〇'
    }
    chineseDigitList = [
        '〇','一','二','三','四','五','六','七','八','九',
        '十','十一','十二','十三','十四','十五','十六','十七','十八','十九',
        '二十','二十一','二十二','二十三','二十四','二十五','二十六','二十七','二十八','二十九',
        '三十', '三十一']
    def genChineseYear(unitStr: str)->str:
        for k, v in chineseDigitDict.items():
            unitStr = unitStr.replace(k, v)
        return unitStr
    year = genChineseYear(d.strftime("%Y"))
    month = chineseDigitList[d.month]
    day = chineseDigitList[d.day]
    return "%s年%s月%s日"%(year, month, day)
def drawDropout(name:str, qq_id:int, d:date=date(2022, 9, 8))->str:
    """绘制退学通知书
    @name: 退学通知书主人公姓名
    @qq_id: 退学通知书右上角标识
    @d: 退学时间

    @return: 退学通知书保存路径
    """
    img = Image.open('resources/images/退学通知书.png')
    pasteLine(img, 567, 1077, name+' 同学:')
    pasteLine(img, 677, 1215, '你已被我校 工科试验班类 专业退学！')
    pasteLine(img, 677, 1363, '请于%s前凭本通知书办理离校手续。'%genChineseDate(d))
    draw = ImageDraw.Draw(img)
    draw.text((2723, 483), str(qq_id), fill=(0, 0, 0, 255), font=FONT_SYHT_M36)
    save_path=os.path.join(SAVE_TMP_PATH, "dropout.png")
    img = img.resize((1096, 768))
    img.save(save_path)
    return save_path

def pasteLine(img, x, y, string):
    left = x
    draw = ImageDraw.Draw(img)
    for s in string:
        if s=='〇':
            draw.text((left, y-10), s, fill=(0, 0, 0, 255), font=FONT_SYST)
            draw.text((left+2, y-10), s, fill=(0, 0, 0, 255), font=FONT_FZXBS)
        else:
            draw.text((left, y), s, fill=(0, 0, 0, 255), font=FONT_FZXBS)
            draw.text((left+1.5, y), s, fill=(0, 0, 0, 255), font=FONT_FZXBS)
        left += (draw.textsize(s, font=FONT_FZXBS)[0] + 4)