from utils.standardPlugin import StandardPlugin, Any, Union, CronStandardPlugin
from utils.responseImage import *
import requests
from bs4 import BeautifulSoup as BS
from utils.basicEvent import *
from utils.basicConfigs import *
from threading import Timer, Semaphore
from pathlib import Path
import json
from datetime import datetime
from urllib.parse import urljoin
import qrcode
import os, os.path
def getSjtuGk():
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
def getSjtuNews():
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

def getJwc()->list:
    pageUrl = 'https://jwc.sjtu.edu.cn/xwtg/tztg.htm'
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
            title:str = content.h2.contents[0]
            link:str = content.a.get('href')
            link = urljoin(pageUrl, link)
            detail:str = content.p.contents[0]
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
class SjtuJwcMonitor(StandardPlugin, CronStandardPlugin):
    monitorSemaphore = Semaphore()
    def __init__(self) -> None:
        if SjtuJwcMonitor.monitorSemaphore.acquire(blocking=False):
            self.start(20, 180)
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return False
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        return "OK"
    def tick(self, ):
        exact_path='data/jwc.json'
        if not os.path.isfile(exact_path):
            with open(exact_path, 'w') as f:
                f.write('[]')
        url_list:list = json.load(open(exact_path, 'r'))
        updateFlag = len(url_list) > 0
        for j in getJwc():
            if j['link'] not in url_list:
                url_list.append(j['link'])
                if not updateFlag: continue
                pic = DrawNoticePIC(j)
                pic = pic if os.path.isabs(pic) else os.path.join(ROOT_PATH, pic)
                for group_id in getPluginEnabledGroups('jwc'):
                    send(group_id, '已发现教务通知更新:\n【'+j['title']+'】\n'+j['link'])
                    send(group_id, '[CQ:image,file=files://%s,id=40000]'%pic)
        with open(exact_path, 'w') as f:
            json.dump(url_list, f, indent=4)
    def getPluginInfo(self, )->Any:
        return {
            'name': 'SjtuJwcMonitor',
            'description': '教务通知更新广播',
            'commandDescription': 'None',
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

class GetSjtuNews(StandardPlugin): 
    monitorSemaphore = Semaphore()
    def __init__(self) -> None:
        self.checkTimer = Timer(20,self.updateAndCheck)
        if GetSjtuNews.monitorSemaphore.acquire(blocking=False):
            self.checkTimer.start()
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg=='-sjtu news'
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        pic_path = os.path.join(SAVE_TMP_PATH, 'sjtu_news.png')
        pic_path = pic_path if os.path.isabs(pic_path) else os.path.join(ROOT_PATH, pic_path)
        if not os.path.isfile(pic_path):
            drawSjtuNews()
        send(target, '[CQ:image,file=files://%s,id=40000]'%pic_path, data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'GetSjtuNews',
            'description': '获取交大新闻网',
            'commandDescription': '-sjtu news',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'fangtiancheng',
        }
    def updateAndCheck(self, ):
        self.checkTimer.cancel()
        self.checkTimer = Timer(900,self.updateAndCheck)
        self.checkTimer.start()
        drawSjtuNews()

def DrawNoticePIC(notice)->str:
    width = 720
    txt_line=""
    txt_parse, title_parse=[], []
    for word in notice['title']:
        if txt_line=="" and word in ['，','；','。','、','"','：','.','”']: #避免标点符号在首位
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
        if txt_line=="" and word in ['，','；','。','、','"','：','.','”']: #避免标点符号在首位
            txt_parse[-1]+=word
            continue
        txt_line+=word
        if font_syhtmed_18.getsize(txt_line)[0]>width-240:
            txt_parse.append(txt_line)
            txt_line=""
    if txt_line!="":
        txt_parse.append(txt_line)
    if txt_parse[-1][-1]!='.':
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
