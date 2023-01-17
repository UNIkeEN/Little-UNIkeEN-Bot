from utils.basicConfigs import *
from utils.basicEvent import *
from typing import Union, Tuple, Any, List, Optional
from utils.standardPlugin import StandardPlugin, CronStandardPlugin
import mysql.connector
from utils.responseImage_beta import *
import wordcloud
import jieba
from io import BytesIO
import re
from threading import Timer, Semaphore
import datetime
import os

def wc_save_path(group_id:int, yesterday_str:str)->str:
    return os.path.join(ROOT_PATH, SAVE_TMP_PATH, f'{group_id}_{yesterday_str}_wordcloud.png')

class GenWordCloud(StandardPlugin, CronStandardPlugin):
    monitorSemaphore = Semaphore()
    def __init__(self):
        self.stopwords = set()

        if GenWordCloud.monitorSemaphore.acquire(blocking=False):
            self.start(5, 60)
            _content = [line.strip() for line in open('resources/corpus/wc_stopwords.txt', 'r', encoding='utf-8-sig').readlines()]
            self.stopwords.update(_content)
    
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return False
    
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        return None
    
    def tick(self):
        now_time = datetime.datetime.now()
        h_m = datetime.datetime.strftime(now_time,'%H:%M')
        yesterday_str=(datetime.date.today() + datetime.timedelta(days=-1)).strftime('%Y-%m-%d')
        if h_m not in ['00:00']: return

        for group_id in APPLY_GROUP_ID:
            wcPic = self.genWordCloud(group_id)
            if wcPic == None: continue
            picPath = wc_save_path(group_id, yesterday_str)
            img = Image.new('RGBA', (860, 670), PALETTE_WHITE)
            draw = ImageDraw.Draw(img)
            draw.rectangle((0,0,859,669), fill=PALETTE_WHITE, outline=PALETTE_GREY_BORDER, width=2)
            img.paste(wcPic, (30,30))
            size0 = draw.textsize('昨 日 词 云', font=FONT_SYHT_M42)
            draw.text((30,590), '昨 日 词 云', fill=PALETTE_BLACK, font=FONT_SYHT_M42)
            draw.text((30+size0[0]+10, 595), '🦄', fill=(209,113,183,255), font=FONT_SYHT_M24)
            size1 = draw.textsize(yesterday_str, font=FONT_SYHT_M24)
            size2 = draw.textsize('群 %d'%group_id, font=FONT_SYHT_M18)
            draw.text((830-size1[0],590), yesterday_str, fill=PALETTE_GREY_SUBTITLE, font=FONT_SYHT_M24)
            draw.text((830-size2[0],600+size1[1]), '群 %d'%group_id, fill=PALETTE_GREY, font=FONT_SYHT_M18)
            img.save(picPath)
            if group_id in getPluginEnabledGroups('wcdaily'):
                send(group_id, '本群昨日词云已生成~','group')
                send(group_id, f'[CQ:image,file=files://{picPath}]','group')
            
    def genWordCloud(self,group_id)->Optional[Image.Image]:
        try:
            mydb = mysql.connector.connect(**sqlConfig)
            mycursor = mydb.cursor()
            mycursor.execute("SELECT message FROM BOT_DATA.messageRecord WHERE group_id=%d and TO_DAYS(NOW( ))-TO_DAYS(time)<=1 and user_id!=%d"%(group_id, BOT_SELF_QQ))
            result=list(mycursor)
            text = []

            for sentence, in result:
                sentence:str
                subsentence = re.split(r'\[CQ[^\]]*\]|\s|\,|\.|\!|\@|\;|。|！|？|：|；|“|”|【|】', sentence)
                subsentence = [re.sub(r'[^\u4e00-\u9fa5]', '', s) for s in subsentence]
                for s in subsentence:
                    text += jieba.cut(s)

            if len(text)<=50:
                return None # 消息过少，不生成词云

            wc = wordcloud.WordCloud(font_path="resources/fonts/SourceHanSansCN-Medium.otf",
                                width = 800,
                                height = 540,
                                background_color='white',
                                min_font_size=6,
                                max_words=120,stopwords=self.stopwords)
            wc.generate(' '.join(text))
            im = wc.to_image()
            return im
        except mysql.connector.Error as e:
            warning("mysql error in getGroupWordCloud: {}".format(e))
        except BaseException as e:
            warning("error in getGroupWordCloud: {}".format(e))
        return None
    def getPluginInfo(self, )->Any:
        return {
            'name': 'GenWordCloud',
            'description': '词云广播',
            'commandDescription': 'None',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }

class wordCloudPlugin(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg=='-wc'
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        yesterday_str=str(datetime.date.today() + datetime.timedelta(days=-1))
        save_path = os.path.join(SAVE_TMP_PATH, str(data['group_id'])+f'_{yesterday_str}_wordcloud.png')
        save_path = os.path.join(ROOT_PATH, save_path)
        if not os.path.exists(save_path):
            send(data['group_id'], "本群未生成昨日词云（可能原因：插件错误或昨日群消息过少）")
        else:
            send(data['group_id'], f'[CQ:image,file=files://{save_path}]','group')
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'wordCloudPlugin',
            'description': '本群昨日词云',
            'commandDescription': '-wc',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }