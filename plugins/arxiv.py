from typing import Any, Union, Dict, List, Tuple, Optional
from utils.standardPlugin import StandardPlugin, CronStandardPlugin
from utils.basicEvent import send, warning
from utils.basicConfigs import ROOT_PATH, SAVE_TMP_PATH, FONTS_PATH
from utils.sqlUtils import newSqlSession
from utils.responseImage_beta import ResponseImage, PALETTE_CYAN
import os, feedparser
from threading import Semaphore
def drawHelpPic(savePath:str):
    helpWords = (
        ""
    )
    helpCards = ResponseImage(
        title = 'arxiv帮助', 
        titleColor = PALETTE_CYAN,
        width = 1000,
        # cardBodyFont= ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 24),
    )
    cardList = []
    cardList.append(('body', helpWords))
    helpCards.addCard(ResponseImage.RichContentCard(
        raw_content=cardList,
        titleFontColor=PALETTE_CYAN,
    ))
    helpCards.generateImage(savePath)

class ArxivHelper(StandardPlugin):
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg in ['arxiv帮助', '-arxiv']
    def executeEvent(self, msg: str, data: Any) -> Optional[str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        helpPicPath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'arxiv-help.png')
        drawHelpPic(helpPicPath)
        send(target, '[CQ:image,file=file:///{}]'.format(helpPicPath), data['message_type'])
        return 'OK'
    def getPluginInfo(self) -> dict:
        return {
            'name': 'ArxivHelper',                      
            'description': 'arxiv帮助',
            'commandDescription': '-arxiv/arxiv帮助',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
        
def createArxivSql():
    mydb, mycursor = newSqlSession()
    mycursor.execute("""create table if not exists `arxivSubscribe`(
        `group_id` bigint unsigned not null,
        `keywords` json not null default cast('[]' as json),
        primary key (`group_id`)
    )charset=utf8mb4, collate=utf8mb4_unicode_ci;""")

def appendKeyword(groupId:int, keyword:str):
    mydb, mycursor = newSqlSession()
    mycursor.execute("""
                     """)
def get_arxiv_rss(labels: str)->Optional[Dict[str, Any]]:
    news = feedparser.parse(f"http://arxiv.org/rss/{labels}")
    if "version" in news:
        return news.entries
    else:
        # Failed getting arxiv RSS, try mirror
        news = feedparser.parse(f"http://arxiv.org/rss/{labels}?mirror=cn")
        if "version" in news:
            return news.entries
        return None
class ArxivSubscriber(StandardPlugin, CronStandardPlugin):
    initGuard = Semaphore()
    def __init__(self) -> None:
        if self.initGuard.acquire(blocking=False):
            createArxivSql()
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return super().judgeTrigger(msg, data)
    def executeEvent(self, msg: str, data: Any) -> Optional[str]:
        return super().executeEvent(msg, data)
    def getPluginInfo(self) -> dict:
        return super().getPluginInfo()        
    