from typing import Any, Optional
from utils.standardPlugin import StandardPlugin, ScheduleStandardPlugin
from utils.basicConfigs import ROOT_PATH, SAVE_TMP_PATH
from utils.basicEvent import send, warning
from utils.configAPI import getPluginEnabledGroups
import requests
from io import BytesIO
from PIL import Image
import datetime
import os, time


def getTodaysMoyuCalendar()->Optional[Image.Image]:
    url = 'https://api.vvhan.com/api/moyu'
    req = requests.get(url)
    if not req.ok:
        return None
    try:
        img = Image.open(BytesIO(req.content))
        return img
    except:
        return None

def getMoyuSavePath()->str:
    today = datetime.date.today()
    filename = today.strftime('moyu-%Y%m%d.png')
    return os.path.join(ROOT_PATH, SAVE_TMP_PATH, filename)

class GetMoyuCalendar(StandardPlugin):
    def __init__(self) -> None:
        self.triggerList = ['-moyu', '摸鱼日历']
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg in self.triggerList
    def executeEvent(self, msg: str, data: Any) -> Optional[str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        filePath = getMoyuSavePath()
        if os.path.isfile(filePath):
            send(target, '[CQ:image,file=file:///{}]'.format(filePath), data['message_type'])
        else:
            img = getTodaysMoyuCalendar()
            if img is None:
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
    def judgeTrigger(self, msg: ROOT_PATH, data: Any) -> bool:
        return False
    def executeEvent(self, msg: ROOT_PATH, data: Any) -> Optional[str]:
        return None
    def tick(self) -> None:
        moyuSavePath = getMoyuSavePath()
        if not os.path.exists(moyuSavePath): 
            while True:
                img = getTodaysMoyuCalendar()
                if img is not None: 
                    img.save(moyuSavePath)
                    break
                time.sleep(180)
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
        