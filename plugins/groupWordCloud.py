from utils.basicConfigs import *
from utils.basicEvent import *
from typing import Union, Tuple, Any, List, Optional
from utils.standardPlugin import StandardPlugin, ScheduleStandardPlugin
from utils.sqlUtils import newSqlSession
from utils.responseImage_beta import *
from utils.configAPI import getPluginEnabledGroups
import wordcloud
import jieba
import re
from threading import Semaphore, Thread
import datetime
import os
from matplotlib import colors

def wc_save_path(group_id:int, yesterday_str:str)->str:
    return os.path.join(ROOT_PATH, SAVE_TMP_PATH, f'{group_id}_{yesterday_str}_wordcloud.png')

class GenPersonWordCloud(StandardPlugin):
    def __init__(self) -> None:
        self.triggerPattern = re.compile(r'^\-wc\s*\[CQ\:at\,qq\=(\d+)\]')
        userdict_path = os.path.join(ROOT_PATH, 'resources/corpus/wc_userdict.txt')
        stopwords_path = os.path.join(ROOT_PATH, 'resources/corpus/wc_stopwords.txt')
        self.stopwords = set([line.strip() for line in open(stopwords_path, 'r', encoding='utf-8-sig').readlines()])
        # if os.path.exists(userdict_path):
        #     jieba.load_userdict(userdict_path)
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return self.triggerPattern.match(msg) != None and data['user_id'] in ROOT_ADMIN_ID
    def executeEvent(self, msg: str, data: Any) -> Optional[str]:
        groupId = data['group_id']
        targetId = int(self.triggerPattern.findall(msg)[0])
        wcPic = self.genWordCloud(groupId, targetId)
        if wcPic == None:
            send(groupId, '用户词云生成失败')
        else:
            savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'userwc_%d_%d.png'%(groupId, targetId))
            wcPic.save(savePath)
            send(groupId, '[CQ:image,file=file:///{}]'.format(savePath))
        return 'OK'
    def genWordCloud(self, group_id:int, user_id:int)->Optional[Image.Image]:
        try:
            mydb, mycursor = newSqlSession(autocommit=False)
            mycursor.execute("SELECT message FROM messageRecord WHERE group_id=%d and user_id=%d"%(group_id, user_id))
            result=list(mycursor)
            text = []

            for sentence, in result:
                sentence:str
                subsentence = re.split(r'\[CQ[^\]]*\]|\s|\,|\.|\!|\@|\;|。|！|？|：|；|“|”|【|】|-', sentence)
                subsentence = [re.sub(r'[^\u4e00-\u9fa5^a-z^A-Z]', '', s) for s in subsentence]
                for s in subsentence:
                    text += jieba.cut(s)

            # color_list = ['#ec1c24', '#ec1c42','#ec3b1c', '#e00d0d', '#fe3f3f', '#f59037', '#f57037', '#fb922a', '#fba42a', '#fbbc2a', '#ffa710', '#ffcb10']
            # colormap = colors.ListedColormap(color_list) # 新春色调

            wc = wordcloud.WordCloud(font_path="resources/fonts/汉仪文黑.ttf",
                                width = 800,
                                height = 540,
                                background_color='white',
                                min_font_size=6,
                                max_words=110,stopwords=self.stopwords,
                                # colormap=colormap
                                )
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
            'name': 'GenPersonWordCloud',
            'description': '用户词云',
            'commandDescription': 'None',
            'usePlace': ['group', ],
            'showInHelp': False,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }

class GenWordCloud(StandardPlugin, ScheduleStandardPlugin):
    monitorSemaphore = Semaphore()
    def __init__(self):
        self.stopwords = set()
        self.userdict_path = os.path.join(ROOT_PATH, 'resources/corpus/wc_userdict.txt')
        self.stopwords_path = os.path.join(ROOT_PATH, 'resources/corpus/wc_stopwords.txt')
        if GenWordCloud.monitorSemaphore.acquire(blocking=False):
            self.schedule(hour=0, minute=0)
            _content = [line.strip() for line in open(self.stopwords_path, 'r', encoding='utf-8-sig').readlines()]
            self.stopwords.update(_content)
            if os.path.exists(self.userdict_path):            
                jieba.load_userdict(self.userdict_path)
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return False
    
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        return None
    
    def tick(self):
        yesterday_str=(datetime.date.today() + datetime.timedelta(days=-1)).strftime('%Y-%m-%d')
        threadPool:List[Thread] = []

        def genSendSaveImg(group_id):
            wcPic = self.genWordCloud(group_id)
            if wcPic == None: return
            picPath = wc_save_path(group_id, yesterday_str)
            img = Image.new('RGBA', (860, 670), PALETTE_WHITE)
            draw = ImageDraw.Draw(img)
            draw.rectangle((0,0,859,669), fill=PALETTE_WHITE, outline=PALETTE_GREY_BORDER, width=2)
            img.paste(wcPic.resize((800, 540)), (30,30))
            size0 = draw.textsize('昨 日 词 云', font=FONT_SYHT_M42)
            draw.text((30,590), '昨 日 词 云', fill=PALETTE_BLACK, font=FONT_SYHT_M42)
            draw.text((30+size0[0]+10, 595), '🦄', fill=(209,113,183,255), font=FONT_SYHT_M24)
            size1 = draw.textsize(yesterday_str, font=FONT_SYHT_M24)
            size2 = draw.textsize('群 %d'%group_id, font=FONT_SYHT_M18)
            draw.text((830-size1[0],590), yesterday_str, fill=PALETTE_GREY_SUBTITLE, font=FONT_SYHT_M24)
            draw.text((830-size2[0],600+size1[1]), '群 %d'%group_id, fill=PALETTE_GREY, font=FONT_SYHT_M18)
            img.save(picPath)
            if group_id in getPluginEnabledGroups('wcdaily'):
                # send(group_id, '本群昨日词云已生成~','group')
                send(group_id, f'[CQ:image,file=file:///{picPath}]','group')
        # end def genSendSaveImg

        for group_id in APPLY_GROUP_ID:
            thread = Thread(target=genSendSaveImg, args=(group_id,))
            thread.daemon = True
            thread.start()
            threadPool.append(thread)

        for thread in threadPool:
            thread.join()

    def genWordCloud(self,group_id)->Optional[Image.Image]:
        try:
            mydb, mycursor = newSqlSession(autocommit=False)
            mycursor.execute("SELECT message FROM messageRecord WHERE group_id=%d and TO_DAYS(NOW( ))-TO_DAYS(time)<=1 and user_id!=%d"%(group_id, BOT_SELF_QQ))
            result=list(mycursor)
            text = []

            for sentence, in result:
                sentence:str
                subsentence = re.split(r'\[CQ[^\]]*\]|\s|\,|\.|\!|\@|\;|。|！|？|：|；|“|”|【|】|-', sentence)
                subsentence = [re.sub(r'[^\u4e00-\u9fa5^a-z^A-Z]', '', s) for s in subsentence]
                for s in subsentence:
                    text += jieba.cut(s)

            if len(text)<=50:
                return None # 消息过少，不生成词云

            color_list = ['#ec1c24', '#ec1c42','#ec3b1c', '#e00d0d', '#fe3f3f', '#f59037', '#f57037', '#fb922a', '#fba42a', '#fbbc2a', '#ffa710', '#ffcb10']
            colormap = colors.ListedColormap(color_list) # 新春色调

            wc = wordcloud.WordCloud(font_path="resources/fonts/汉仪文黑.ttf",
                                width = 800,
                                height = 540,
                                background_color='white',
                                min_font_size=6,
                                max_words=110,stopwords=self.stopwords,
                                colormap=colormap)
            
            # # MC群专属
            # if group_id == 712514518:
            #     mask_img = np.array(Image.open('resources/images/genshin/2.png'))
            #     color_func = wordcloud.ImageColorGenerator(mask_img)
            #     wc = wordcloud.WordCloud(font_path="resources/fonts/汉仪文黑.ttf",
            #                         width = 2133,
            #                         height = 1440,
            #                         background_color='white',
            #                         min_font_size=2,max_font_size=150,relative_scaling=0.4,
            #                         max_words=600,stopwords=self.stopwords,
            #                         colormap=colormap,
            #                         color_func=color_func,
            #                         mask=mask_img)
                                    
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
            send(data['group_id'], f'[CQ:image,file=file:///{save_path}]','group')
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