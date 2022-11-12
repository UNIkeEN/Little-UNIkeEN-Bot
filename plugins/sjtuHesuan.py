from utils.basicConfigs import ROOT_PATH, SAVE_TMP_PATH
from utils.basicEvent import send, warning
from typing import Union, Tuple, Any, List
from utils.standardPlugin import StandardPlugin
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, date, time, timedelta
import numpy as np
import json, os.path
import re
from utils.responseImage import *


class SjtuHesuan(StandardPlugin):
    @staticmethod
    def xyToUv(lng:float, lat:float)->Tuple[int, int]:
        loc = np.matrix([[lng], [lat], [1.0]], dtype = np.float64)
        convert = np.matrix([
            [19.0, 1458.0, 10.0],
            [13.0, 27.0, 834.0],
            [1.0, 1.0, 1.0]
        ], dtype = np.float64) * np.matrix([
            [121.429318, 121.4524, 121.434272],
            [31.033855, 31.041409, 31.022526],
            [1.0, 1.0, 1.0]
        ], dtype = np.float64).I
        uv = convert * loc
        return int(uv[0, 0]), int(uv[1, 0])
    @staticmethod
    def getLocColor(openTime: str, daily: bool):
        """获取核酸点位渲染颜色
        @openTime: like '8:00-10:00'
        @return:   圈的颜色, 字的颜色
        """
        def parseTime(timeStr, nowTime: datetime):
            timeParser = re.compile(r'^(\d+):(\d+)-(\d+):(\d+)$')
            t00, t01, t10, t11 = timeParser.findall(timeStr)[0]
            return datetime.combine(nowTime.date(), time(int(t00), int(t01))), \
                   datetime.combine(nowTime.date(), time(int(t10), int(t11)))
        nowTime = datetime.now()
        if not daily and nowTime.isoweekday() >= 6:
            return PALETTE_GREY, PALETTE_GREY
        else:
            for openTime in openTime.split(','):
                startTime, endTime = parseTime(openTime, nowTime)
                warningTime = endTime - timedelta(minutes=20)
                if startTime <= nowTime and nowTime < warningTime:
                    return PALETTE_GREEN, PALETTE_BLACK
                elif warningTime <= nowTime and nowTime < endTime:
                    return PALETTE_ORANGE, PALETTE_BLACK
            return PALETTE_GREY, PALETTE_GREY
            
    def __init__(self) -> None:
        self.hesuanList = json.load(open('resources/sjtuHesuan.json', 'r'))
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg == '-hs'
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        hesuanMap = Image.open('resources/images/hesuanMap.png')
        draw = ImageDraw.Draw(hesuanMap)
        for loc in self.hesuanList:
            lng = loc['point']['lng']
            lat = loc['point']['lat']
            x, y = SjtuHesuan.xyToUv(lng, lat)
            r = 10
            circleFill, wordFill = SjtuHesuan.getLocColor(loc['time'], loc['timeTitle'] == '每天')
            draw.ellipse((x-r, y-r, x+r, y+r), fill=circleFill)
            showText = loc['title']+'\n'+loc['timeTitle']+' '+loc['time']
            titlesize = draw.textsize(showText, FONT_SYHT_M18)
            tmp = ResponseImage()
            if loc['title'] in ['X86', '西三区广场', '化工学院', '包玉刚图书馆', '船建学院', 'X56', 'D28', 'D35', 'D25']:
                tmp.drawRoundedRectangle(x-titlesize[0]/2-10, y+15, x+titlesize[0]/2+10, y+35+titlesize[1], fill = PALETTE_WHITE, border = True, target = hesuanMap)
                draw.text((x-titlesize[0]/2, y+25), showText, wordFill , FONT_SYHT_M18)
            else:
                tmp.drawRoundedRectangle(x-titlesize[0]/2-10, y-35-titlesize[1], x+titlesize[0]/2+10, y-15, fill = PALETTE_WHITE, border = True, target = hesuanMap)
                draw.text((x-titlesize[0]/2, y-25-titlesize[1]), showText, wordFill , FONT_SYHT_M18)
        savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'hesuan-%d.png'%target)
        hesuanMap.save(savePath)
        send(target, f'[CQ:image,file=files://{savePath},id=40000]', data['message_type'])

    def getPluginInfo(self, )->Any:
        return {
            'name': 'SjtuHesuan',
            'description': '核酸查询',
            'commandDescription': '-hs',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.3',
            'author': 'Unicorn',
        }
if __name__ == '__main__':
    print(SjtuHesuan.xyToUv(121.44312, 31.032327))
    print(SjtuHesuan.xyToUv(121.429318, 31.033855))