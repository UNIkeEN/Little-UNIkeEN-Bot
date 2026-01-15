import datetime
import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import requests
from utils.basicConfigs import ROOT_PATH, SAVE_TMP_PATH
from utils.basicEvent import send, warning
from utils.configAPI import getPluginEnabledGroups
from utils.responseImage_beta import *
from utils.sqlUtils import newSqlSession
from utils.standardPlugin import (CronStandardPlugin, NotPublishedException,
                                  StandardPlugin)

def createSjmclSql():
    mydb, mycursor = newSqlSession()
    mycursor.execute("""create table if not exists `sjmclVersions` (
        `tag_name` VARCHAR(20) not null,
        `created_at` timestamp not null,
        primary key (`created_at`)
    )""")

def getSjmclInfo()->Optional[Dict[str,Any]]:
    url = 'https://api.github.com/repos/UNIkeEN/SJMCL/releases/latest'
    req = requests.get(url)
    if req.status_code != requests.codes.ok:
        return None
    try:
        return req.json()
    except:
        return None
    

def convertReleaseNotes(body: str):
    EMOJI_COLOR = {
        '🔥': PALETTE_SJTU_RED,
        '🌟': PALETTE_SJTU_ORANGE,
        '🐛': PALETTE_SJTU_GREEN,
        '⚡️': PALETTE_SJTU_CYAN,
        '💄': PALETTE_SJTU_BLUE,
        '🛠': PALETTE_SJTU_BLUE,
        '📦': PALETTE_SJTU_DARKBLUE,
    }
    tuples = []
    for raw in body.replace('\r', '').splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith('---'):
            tuples.append(('separator', ))
            continue
        if line.startswith('- '):
            line = line[2:]

        first_token = line.split(' ', 1)[0] if line else ''
        color = None
        for k, v in EMOJI_COLOR.items():
            if first_token.startswith(k):
                color = v
                break

        tuples.append(('body', line, color) if color else ('body', line))
    return tuples

def drawSjmclInfo(sjmclInfo: Dict[str, Any], savePath:str)->bool:
    card = ResponseImage(
        titleColor = PALETTE_SJTU_BLUE,
        title = 'SJMCL Release',
        layout = 'normal',
        width = 1200,
        footer=datetime.datetime.now().strftime('更新于 %Y-%m-%d  %H:%M:%S'),
        cardBodyFont= ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 24),
        cardSubtitleFont= ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 30),
    )
    published_at = datetime.datetime.strptime(sjmclInfo['published_at'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc).astimezone()
    
    card.addCardList([
        ResponseImage.RichContentCard(
            raw_content=[
                # ('illustration', 'https://raw.githubusercontent.com/UNIkeEN/SJMCL/main/docs/figs/banner.png'),
                ('title', sjmclInfo['name']),
                ('separator', ),
                ('subtitle', published_at.strftime('发布于 %Y-%m-%d  %H:%M:%S')),
            ],
        ),
        ResponseImage.RichContentCard(
            raw_content=convertReleaseNotes(sjmclInfo['body'])
        )
    ])
    card.generateImage(savePath)
    return True

class GetSjmclRelease(StandardPlugin):
    def __init__(self,):
        pass
        
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg.lower() in ['-sjmcl']
    
    def executeEvent(self, msg: str, data: Any) -> Optional[str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        sjmclInfo = getSjmclInfo()
        if sjmclInfo == None:
            send(target, '获取 SJMCL 版本失败，请稍后重试', data['message_type'])
        else:
            savePath = os.path.join(ROOT_PATH,SAVE_TMP_PATH,'sjmcl.png')
            succ = drawSjmclInfo(sjmclInfo, savePath)
            if succ:
                send(target, '[CQ:image,file=file:///{}]'.format(savePath), data['message_type'])
                send(target, sjmclInfo['html_url'], data['message_type'])
            else:
                send(target, 'SJMCL 版本解析失败', data['message_type'])
        return 'OK'

    def getPluginInfo(self) -> dict:
        return {
            'name': 'GetSjmclRelease',
            'description': '获取 SJMCL 版本',
            'commandDescription': '-sjmcl',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }

def checkSjmclUpdate(sjmclInfo: Dict[str, Any])->bool:
    tag_name = sjmclInfo['tag_name']
    created_at = datetime.datetime.strptime(sjmclInfo['created_at'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc).astimezone()
    mydb, mycursor = newSqlSession()
    mycursor.execute("""select count(*) from `sjmclVersions` where `created_at` = %s""", (created_at,))
    result = list(mycursor)
    if result[0][0] == 0:
        mycursor.execute("insert ignore into `sjmclVersions` (`created_at`, `tag_name`) values (%s, %s)",
        (created_at, tag_name))
        return True
    else:
        return False

    
class SjmclMonitor(StandardPlugin,CronStandardPlugin):
    initGuard = True
    def __init__(self,):
        self.job = None
        if self.initGuard:
            self.initGuard = False
            createSjmclSql()
            self.job = self.start(0, 60)
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return False
    def executeEvent(self, msg: str, data: Any) -> Optional[str]:
        return None
    def tick(self) -> None:
        sjmclInfo = getSjmclInfo()
        if sjmclInfo == None:
            return
        if checkSjmclUpdate(sjmclInfo):
            savePath = os.path.join(ROOT_PATH,SAVE_TMP_PATH,'sjmcl-monitor.png')
            succ = drawSjmclInfo(sjmclInfo, savePath)
            if not succ:
                warning('SJMCL 更新图片绘制失败')
            else:
                for groupId in getPluginEnabledGroups('sjmc'):
                    send(groupId, 'SJMCL 已发布新版本：{}'.format(sjmclInfo['html_url']))
                    send(groupId, '[CQ:image,file=file:///{}]'.format(savePath))

        
    def getPluginInfo(self) -> dict:
        return {
            'name': 'SjmclMonitor',
            'description': 'SJMCL 更新播报',
            'commandDescription': '-grpcfg驱动',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
        