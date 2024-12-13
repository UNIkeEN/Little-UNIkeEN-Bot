from typing import Any, Optional
from utils.standardPlugin import StandardPlugin, ScheduleStandardPlugin
from utils.basicConfigs import ROOT_PATH, SAVE_TMP_PATH
from utils.basicEvent import send, warning
from utils.configAPI import getPluginEnabledGroups
import requests
from io import BytesIO
from PIL import Image
import datetime
import os, time, re
from urllib import parse as urlparse
import numpy as np

def getTodaysMoyuCalendar()->Optional[Image.Image]:
    url = 'https://api.j4u.ink/proxy/remote/moyu.json'
    req = requests.get(url)
    if not req.ok:
        return None
    reqJson = req.json()
    if reqJson['code'] != 200:
        return None
    picUrl = reqJson.get('data', {}).get('moyu_url', None)
    if picUrl == None: return None
    dateStr = os.path.splitext(os.path.basename(urlparse.urlparse(picUrl).path))[0]
    datePattern = re.compile(r'^(\d{4})(\d{2})(\d{2})$')
    if datePattern.match(dateStr) == None: 
        warning('moyu API failed')
        return None
    year, month, day = datePattern.findall(dateStr)[0]
    today = datetime.date.today()
    if int(year) != today.year or int(month) != today.month or int(day) != today.day:
        return None
    picReq = requests.get(picUrl)
    if not picReq.ok: return None
    try:
        img = Image.open(BytesIO(picReq.content))
        return img
    except Exception as e:
        return None

def getMoyuSavePath(date:Optional[datetime.date]=None)->str:
    if date is None:
        date = datetime.date.today()
    filename = date.strftime('moyu-%Y%m%d.png')
    return os.path.join(ROOT_PATH, SAVE_TMP_PATH, filename)

def checkSameWithYesterday(img:Image.Image)->bool:
    yesterday = datetime.date.today() + datetime.timedelta(days=-1)
    yesterdayImgPath = getMoyuSavePath(yesterday)
    if not os.path.exists(yesterdayImgPath):
        return False
    try:
        yesterdayImg = Image.open(yesterdayImgPath)
        img:np.ndarray = np.asarray(img)
        yesterdayImg:np.ndarray = np.asarray(yesterdayImg)
        if img.shape != yesterdayImg.shape:
            return False
        return np.all(img == yesterdayImg)
    except:
        return False

class GetMoyuCalendar(StandardPlugin):
    def __init__(self) -> None:
        self.triggerList = ['-moyu', '摸鱼日历']
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg in self.triggerList
    def executeEvent(self, msg: str, data: Any) -> Optional[str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        filePath = getMoyuSavePath()
        if os.path.isfile(filePath):
            img = Image.open(filePath)
            if not checkSameWithYesterday(img):
                send(target, '[CQ:image,file=file:///{}]'.format(filePath), data['message_type'])
        else:
            img = getTodaysMoyuCalendar()
            if img is None:
                send(target, '摸鱼日历尚未更新', data['message_type'])
            elif checkSameWithYesterday(img):
                img.save(filePath)
                send(target, '摸鱼日历尚未更新', data['message_type'])
            else:
                img.save(filePath)
                send(target, '[CQ:image,file=file:///{}]'.format(filePath), data['message_type'])
        return 'OK'
    def getPluginInfo(self) -> dict:
        return {
            'name': 'GetMoyuCalendar',
            'description': '摸鱼日历',
            'commandDescription': '-moyu / 摸鱼日历',
            'usePlace': ['group', 'private'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
        
class UpdateMoyuCalendar(StandardPlugin, ScheduleStandardPlugin):
    guard = True
    def __init__(self) -> None:
        self.job = None
        if self.guard:
            self.guard = False
            self.job = self.schedule(hour=8, minute=0)
    def judgeTrigger(self, msg: Any, data: Any) -> bool:
        return False
    def executeEvent(self, msg: Any, data: Any) -> Optional[str]:
        return None
    def tick(self) -> None:
        moyuSavePath = getMoyuSavePath()
        while True:
            if os.path.exists(moyuSavePath): 
                img = Image.open(moyuSavePath)
            else:
                img = getTodaysMoyuCalendar()
                if img is not None: 
                    img.save(moyuSavePath)
            if img is None:
                time.sleep(180)
                continue
            elif checkSameWithYesterday(img):
                return
            else:
                break
        for group_id in getPluginEnabledGroups('newsreport'):
            send(group_id, f'[CQ:image,file=file:///{moyuSavePath}]')
    def getPluginInfo(self) -> dict:
        return {
            'name': 'UpdateMoyuCalendar',
            'description': '摸鱼日历播报',
            'commandDescription': 'None',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
        