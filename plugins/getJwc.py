import json
import os
import os.path
from datetime import datetime
from threading import Semaphore
from typing import Any, Dict, List, Set, Union
from urllib.parse import urljoin

import mysql.connector
import qrcode
import requests
from bs4 import BeautifulSoup as BS

from utils.basicConfigs import *
from utils.basicEvent import (draw_rounded_rectangle, init_image_template,
                              send, warning)
from utils.configAPI import getPluginEnabledGroups
from utils.responseImage import *
from utils.sqlUtils import newSqlSession
from utils.standardPlugin import (CronStandardPlugin, GuildStandardPlugin,
                                  StandardPlugin)


def createJwcSql() -> None:
    mydb, mycursor = newSqlSession()
    mycursor.execute("""
    create table if not exists `sjtuJwc` (
        `jwc_seq` bigint unsigned not null auto_increment,
        `url` varchar(100) not null,
        `update_time` timestamp default null,
        primary key (`jwc_seq`)
    )charset=utf8mb4, collate=utf8mb4_unicode_ci;""")

def appendJwcUrl(url:str) -> None:
    mydb, mycursor = newSqlSession()
    mycursor.execute("""
    insert into `sjtuJwc` (`url`, `update_time`) values (%s, %s)
    """, (url, datetime.now()))

def getSjtuGk() -> List[Dict[str, Any]]:
    """交大信息公开网"""
    pageUrl = 'https://gk.sjtu.edu.cn'
    req = requests.get(pageUrl)
    if req.status_code != requests.codes.ok:
        warning("gk.sjtu.edu.cn API failed!")
        return []
    html = req.text
    html = BS(html, 'lxml')
    news = html.find(class_='new-ncon').find_all('li')
    result = []
    for n in news:
        try:
            category = n.i.contents[0]
            link = n.a.get('href')
            link = urljoin(pageUrl, link)
            title = n.a.contents[0]
            result.append({
                'category': category,
                'link': link,
                'title': title
            })
        except BaseException as e:
            print("exception in getSjtuGk: {}".format(e))
    return result

def loadPrevUrls()->Set[str]:
    mydb, mycursor = newSqlSession(autocommit=False)
    mycursor.execute("""
    select `url` from `sjtuJwc`
    """)
    result = set()
    for url, in list(mycursor):
        result.add(url)
    return result

def getSjtuNews() -> List[Dict[str, Any]]:
    """交大新闻网"""
    pageUrl = 'https://news.sjtu.edu.cn/jdyw/index.html'
    req = requests.get(pageUrl)
    if req.status_code != requests.codes.ok:
        warning("news.sjtu.edu.cn API failed!")
        return []
    html = req.text
    html = BS(html, 'lxml')
    news = html.find('div', class_='list-card-h').find_all('li', class_='item')
    result = []
    for n in news:
        card = n.find('a', class_='card')
        try:
            link =  card.get('href')
            link = urljoin(pageUrl, link)
        except:
            link = None
        try:
            imgLink = card.find('img').get('src')
            imgLink = urljoin(pageUrl, imgLink)
        except:
            imgLink = None
        try:
            title = card.find('p', class_='dot').contents[0]
        except:
            title = None
        try:
            detail = card.find('div', class_='des dot').contents[0]
        except:
            detail = None
        about = card.find('div', class_='time')
        try:
            time = about.find('span').contents[0]
        except:
            time = None
        try:
            source = about.find('div', class_='source').p.contents[0]
        except:
            source = None
        result.append({
            'title': title,
            'link': link,
            'imgLink': imgLink,
            'detail': detail,
            'time': time,
            'source': source
        })
    return result

def drawSjtuNews()->str:
    a = ResponseImage(
        title='交大新闻', 
        titleColor=PALETTE_SJTU_RED, 
        primaryColor=PALETTE_SJTU_RED, 
        footer='update at %s'%datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M"),
        layout='normal'
    )
    for news in sorted(getSjtuNews(), key=lambda x: x['time'], reverse=True):
        if news['source'] == None:
            keyword = news['time']
        else:
            keyword = news['source'] + '  ' + news['time']
        a.addCard({
            'style': 'normal',
            'title': news['title'],
            'keyword': keyword,
            'body': news['detail'],
            'icon': news['imgLink']
        })
    savePath = os.path.join(SAVE_TMP_PATH, 'sjtu_news.png')
    a.generateImage(savePath)
    return savePath

def getJwcPage(pageUrl:str)->List[Dict[str, Any]]:
    req = requests.get(pageUrl)
    if req.status_code != requests.codes.ok:
        warning("jwc.sjtu.edu.cn API failed!")
        return []
    page = str(req.content, 'utf-8')
    page = BS(page, 'lxml')
    news = page.find(class_='Newslist').ul.find_all(class_='clearfix')
    newsList = []
    for n in news:
        try:
            sj = n.find(class_='sj')
            year, month = sj.p.contents[0].split('.')
            day = sj.h2.contents[0]
            content = n.find(class_='wz')
            try:
                title:str = content.h2.contents[0]
            except:
                title = None
            link:str = content.a.get('href')
            link = urljoin(pageUrl, link)
            try:
                detail:str = content.p.contents[0]
            except:
                detail = ''
            newsList.append({
                'year': year,
                'month': month,
                'day': day,
                'title': title,
                'detail': detail,
                'link': link,
            })
        except BaseException as e:
            print("exception in getJwc: {}".format(e))
    return newsList

def mergeJwcList(jwcDicts:List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    result = []
    pageUrls = set()
    for d in jwcDicts:
        for jwcPage in d:
            link = jwcPage['link']
            if link in pageUrls: continue
            pageUrls.add(link)
            result.append(jwcPage)
    return result
            
def getJwc() -> List[Dict[str, Any]]:
    jwcUrls = ['https://jwc.sjtu.edu.cn/xwtg/tztg.htm',
               'https://jwc.sjtu.edu.cn/index/mxxsdtz.htm']
    jwcDicts = []
    for url in jwcUrls:
        jwcDicts.append(getJwcPage(url))
    return mergeJwcList(jwcDicts)

class SjtuJwcMonitor(StandardPlugin, CronStandardPlugin):
    monitorSemaphore = Semaphore()
    def __init__(self) -> None:
        if SjtuJwcMonitor.monitorSemaphore.acquire(blocking=False):
            self.start(20, 30)
            createJwcSql()
        self.url_list = []
        if False:
            if not os.path.isfile(exact_path):
                with open(exact_path, 'w') as f:
                    f.write('[]')
            self.url_list:list = json.load(open(exact_path, 'r'))
        else:
            self.url_list = list(loadPrevUrls())
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return False
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        return "OK"
    def tick(self, ):
        exact_path= os.path.join(ROOT_PATH, 'data/jwc.json')
        updateFlag = len(self.url_list) > 0
        for j in getJwc():
            if j['link'] in self.url_list: continue
            self.url_list.append(j['link'])
            appendJwcUrl(j['link'])
            if not updateFlag: continue
            pic = DrawNoticePIC(j)
            pic = pic if os.path.isabs(pic) else os.path.join(ROOT_PATH, pic)
            broadcastWord = '已发现教务通知更新:\n【'+j['title']+'】\n'+j['link']
            for group_id in getPluginEnabledGroups('jwc'):
                send(group_id, broadcastWord)
                send(group_id, '[CQ:image,file=file:///%s]'%pic)
            if False:
                with open(exact_path, 'w') as f:
                    json.dump(self.url_list, f, indent=4)
    def getPluginInfo(self, )->Any:
        return {
            'name': 'SjtuJwcMonitor',
            'description': '教务通知更新广播',
            'commandDescription': '[-grpcfg驱动]',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.4',
            'author': 'Unicorn',
        }

class GetJwc(StandardPlugin): 
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg=='-jwc'
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        jwc = sorted(getJwc(), key=lambda x: '%s-%s-%s'%(x['year'], x['month'], x['day']), reverse=True)
        jwcStr = ""
        idx = 1
        for j in jwc[:7]:
            jwcStr += '【%d】%s-%s-%s %s %s\n'%(idx, j['year'], j['month'], j['day'], j['title'], j['link'])
            idx += 1
        jwcStr = jwcStr[:-1]
        send(target, jwcStr, data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'GetJwc',
            'description': '获取教务通知',
            'commandDescription': '-jwc',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
    def checkSelfStatus(self):
        jwc = sorted(getJwc(), key=lambda x: '%s-%s-%s'%(x['year'], x['month'], x['day']), reverse=True)
        return 1, 1, '正常'
    
class SubscribeJwc(StandardPlugin):
    initGuard = Semaphore()
    # https://docs.python.org/3/faq/library.html#what-kinds-of-global-value-mutation-are-thread-safe
    subscribers = set()
    def __init__(self) -> None:
        if SubscribeJwc.initGuard.acquire(blocking=False):
            mydb, mycursor = newSqlSession()
            mycursor.execute("""
            create table if not exists `jwcSubscriber`(
                `user_id` bigint not null,
                `subscribe_time` timestamp not null,
                primary key(`user_id`)
            );""")
            mycursor.execute("select `user_id` from `jwcSubscriber`")
            for user_id, in list(mycursor):
                SubscribeJwc.subscribers.add(user_id)
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg in ['订阅教务处', '取消订阅教务处']
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        subscribe = msg == '订阅教务处'
        user_id = data['user_id']
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        mydb, mycursor = newSqlSession()
        try:
            if subscribe:
                if user_id in SubscribeJwc.subscribers:
                    send(target,"[CQ:reply,id=%d]订阅失败，您已订阅"%data['message_id'], data['message_type'])
                else:
                    SubscribeJwc.subscribers.add(user_id)
                    mydb, mycursor = newSqlSession()
                    mycursor.execute("""
                    insert ignore into `jwcSubscriber` (`user_id`, `subscribe_time`)
                    values (%d, from_unixtime(%d));"""%(
                        user_id,
                        data['time']
                    ))
                    send(target, "[CQ:reply,id=%d]订阅成功，注意添加bot好友接收通知信息"%data['message_id'], data['message_type'])
            else:
                if user_id not in SubscribeJwc.subscribers:
                    send(target,"[CQ:reply,id=%d]取消订阅失败，您尚未订阅"%data['message_id'], data['message_type'])
                else:
                    SubscribeJwc.subscribers.remove(user_id)
                    mycursor.execute("""
                    delete from `jwcSubscriber` where `user_id` = %d
                    """%data['user_id'])
                    send(target,"[CQ:reply,id=%d]取消订阅成功"%data['message_id'], data['message_type'])
        except mysql.connector.Error as e:
            warning('mysql exception in SubscribeJwc: {}'.format(e))
            send(target,"[CQ:reply,id=%d]操作失败"%data['message_id'], data['message_type'])
        except BaseException as e:
            warning('base exception in SubscribeJwc: {}'.format(e))
            send(target,"[CQ:reply,id=%d]操作失败"%data['message_id'], data['message_type'])
        return "OK"
    @staticmethod
    def getJwcSubscribers()->Set[int]:
        return SubscribeJwc.subscribers
    def getPluginInfo(self) -> dict:
        return {
            'name': 'SubscribeJwc',
            'description': '教务处订阅',
            'commandDescription': '订阅教务处/取消订阅教务处',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': ['jwcSubscriber'],
            'version': '1.0.3',
            'author': 'Unicorn',
        }
        
class GetSjtuNews(StandardPlugin, CronStandardPlugin): 
    monitorSemaphore = Semaphore()
    def __init__(self) -> None:
        if GetSjtuNews.monitorSemaphore.acquire(blocking=False):
            # self._tick()
            self.start(0, 30 * 60)
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg in ['-sjtu news', '交大新闻']
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        pic_path = os.path.join(SAVE_TMP_PATH, 'sjtu_news.png')
        pic_path = pic_path if os.path.isabs(pic_path) else os.path.join(ROOT_PATH, pic_path)
        if not os.path.isfile(pic_path):
            drawSjtuNews()
        send(target, '[CQ:image,file=file:///%s]'%pic_path, data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'GetSjtuNews',
            'description': '获取交大新闻网',
            'commandDescription': '-sjtu news/交大新闻',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'fangtiancheng',
        }
        
    def tick(self, ):
        drawSjtuNews()
        
    def checkSelfStatus(self):
        drawSjtuNews()
        return 1, 1, '正常'
    
def DrawNoticePIC(notice)->str:
    width = 720
    txt_line=""
    txt_parse, title_parse=[], []
    for word in notice['title']:
        if len(title_parse) > 0 and txt_line=="" and word in ['，','；','。','、','"','：','.','”']: #避免标点符号在首位
            title_parse[-1]+=word
            continue
        txt_line+=word
        if font_syhtmed_24.getsize(txt_line)[0]>width-180:
            title_parse.append(txt_line)
            txt_line=""
    if txt_line!="":
        title_parse.append(txt_line)

    txt_line=""
    for word in notice['detail'].strip():
        if len(txt_parse) > 0 and txt_line=="" and word in ['，','；','。','、','"','：','.','”']: #避免标点符号在首位
            txt_parse[-1]+=word
            continue
        txt_line+=word
        if font_syhtmed_18.getsize(txt_line)[0]>width-240:
            txt_parse.append(txt_line)
            txt_line=""
    if txt_line!="":
        txt_parse.append(txt_line)
    if len(txt_parse) > 0 and len(txt_parse[-1]) > 0 and txt_parse[-1][-1]!='.':
        txt_parse[-1]+='...'
    height = 525+len(txt_parse)*27+len(title_parse)*33
    img, draw, h = init_image_template('教务通知·更新提醒', width, height, (167,32,56,255))
    h+=130
    l=60
    img=draw_rounded_rectangle(img, 60, h, width-60, height-90, (255,255,255,255))
    txt_size=draw.textsize(notice['title'], font = font_syhtmed_24)
    for line in title_parse:
        txt_size=draw.textsize(line, font = font_syhtmed_24)
        draw.text(((width-txt_size[0])/2,h+33), line, fill=(0,0,0,255),font = font_syhtmed_24)
        h+=33
    # draw.text(((width-txt_size[0])/2,h+30),notice['title'], fill=(0,0,0,255),font = font_syhtmed_24)
    # h+=(30+txt_size[1])
    h+=5
    time_txt = '%s-%s-%s'%(notice['year'], notice['month'], notice['day'])
    txt_size=draw.textsize(time_txt, font = font_syhtmed_18)
    draw.text(((width-txt_size[0])/2,h+30),time_txt, fill=(115,115,115,255),font = font_syhtmed_18)
    h+=(30+txt_size[1])
    for line in txt_parse:
        txt_size=draw.textsize(line, font = font_syhtmed_18)
        draw.text(((width-txt_size[0])/2,h+27), line, fill=(115,115,115,255),font = font_syhtmed_18)
        h+=27
    qrc = qrcode.QRCode(
        version=3,
        error_correction=qrcode.constants.ERROR_CORRECT_Q,
        box_size=15,
        border=4,
    )
    qrc.add_data(notice['link'])
    qrc.make(fit=True)
    imgqrc = qrc.make_image().resize((180,180))
    img.paste(imgqrc, ((width-180)//2,h+30))
    save_path=os.path.join(SAVE_TMP_PATH, 'jwc_notice.png')
    img.save(save_path)
    return save_path

if __name__ == '__main__':
    createJwcSql()
    exact_path= os.path.join(ROOT_PATH, 'data/jwc.json')
    with open(exact_path, 'r') as f:
        jwcUrls = json.load(f)
    for url in jwcUrls:
        appendJwcUrl(url)