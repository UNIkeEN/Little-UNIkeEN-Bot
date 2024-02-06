import requests
from lxml import etree
from PIL import Image, ImageDraw, ImageFont
import datetime
import re
from typing import Union, Any, Optional, Dict
from utils.basicEvent import *
from utils.basicConfigs import *
from utils.standardPlugin import StandardPlugin, CronStandardPlugin
from threading import Semaphore
from utils.configAPI import getPluginEnabledGroups
from dateutil import parser as timeparser

class ShowNews(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return (msg in ['每日新闻','新闻'])
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        today_exist, today_pic_str = get_news_pic_path(datetime.date.today())
        if today_exist:
            send(target, f'[CQ:image,file=file:///{today_pic_str}]', data['message_type'])
        else:
            send(target, "获取失败\n新闻源尚未更新本日新闻", data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'ShowNews',
            'description': '新闻',
            'commandDescription': '每日新闻/新闻',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': '北极づ莜蓝',
        }

class YesterdayNews(StandardPlugin):
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg in ['昨日新闻']
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        today_exist, today_pic_str = get_news_pic_path(datetime.date.today() + datetime.timedelta(days=-1))
        if today_exist:
            send(target, f'[CQ:image,file=file:///{today_pic_str}]', data['message_type'])
        else:
            send(target, "bot开小差了，昨日新闻没保存QAQ", data['message_type'])
        return "OK"
    def getPluginInfo(self) -> dict:
        return {
            'name': 'YesterdayNews',
            'description': '昨日新闻',
            'commandDescription': '昨日新闻',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': '北极づ莜蓝',
        }

class UpdateNewsAndReport(StandardPlugin, CronStandardPlugin):
    guard = Semaphore()
    def __init__(self) -> None:
        self.job = None
        if UpdateNewsAndReport.guard.acquire(blocking=False):
            self.job = self.start(0, 3 * 60)
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return False
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        return None
    def tick(self) -> None:
        exist, today_pic_str = get_news_pic_path(datetime.date.today())
        if exist: return

        today_pic = get_todays_news()
        if today_pic is None:
            return
        else:
            today_pic.save(today_pic_str)
        for group_id in getPluginEnabledGroups('newsreport'):
            send(group_id, f'[CQ:image,file=file:///{today_pic_str}]')
                
    def getPluginInfo(self) -> dict:
        return {
            'name': 'UpdateNewsAndReport',
            'description': '新闻播报',
            'commandDescription': 'None',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': '北极づ莜蓝',
        }

def get_news_pic_path(date: datetime.date)->Tuple[bool, str]:
    """获取对应日期的新闻图片路径，并判断路径是否存在
    @date: 新闻日期

    @return: {
        @0: 路径是否存在
        @1: 新闻图片绝对路径
    }
    """
    date_str = str(date)
    pic_path = os.path.join(ROOT_PATH, SAVE_TMP_PATH, f'{date_str}_news.png')
    exist = os.path.isfile(pic_path)
    return exist, pic_path

def get_todays_news()->Optional[Image.Image]:
    url = 'https://api.jun.la/60s.php?format=imgapi'
    try:
        req = requests.get(url).json()
        if req['msg'] != 'success':
            return None
        imgUrl = req['imageBaidu']
        imgDate = timeparser.parse(req['imageTime']).date()
        today = datetime.date.today()
        if imgDate != today:
            return None
        imgReq = requests.get(imgUrl)
        if not imgReq.ok:
            return None
        img = Image.open(BytesIO(imgReq.content))
        return img
    except:
        return None