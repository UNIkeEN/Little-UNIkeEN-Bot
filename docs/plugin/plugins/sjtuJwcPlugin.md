## 1. 插件简介

| 插件名称 | 父类 | 触发关键词 | 触发权限 | 内容 |
| ---- | ---- | ---- | ---- | ---- |
| JwcGroup | PluginGroupManager | '-jwc' | None | 获取交大教务处信息 |

## 2. 示范样例

代码部分：

```python
ROOT_ADMIN_ID = [111, # 用户A  
                 222, # 用户B
                 444] # 用户D
GroupPluginList = [ # 群聊启用插件
    # .....
    JwcGroup()
    # .....
]
```

群聊部分：

```bash
# 群内尚未打开jwc
333> -jwc
# 无事发生

# 接下来管理员打开canvas
111> -grpcfg enable jwc
bot> OK

# 用户发送jwc指令
222> -jwc
bot>    【1】2022-09-30 2022年大学生英语竞赛闵行校区考生退费通知 https://jwc.sjtu.edu.cn/info/1285/11905.htm
        【2】2022-09-30 关于上海交通大学2022年立项教材评审结果的公示 https://jwc.sjtu.edu.cn/info/1257/11904.htm
        【3】2022-09-29 关于举办第十四届全国大学生数学竞赛赛前培训的通知 https://jwc.sjtu.edu.cn/info/1222/11900.htm
        【4】2022-09-27 上海交通大学2023年推荐优秀应届本科毕业生免试攻读研究生公示名单 https://jwc.sjtu.edu.cn/content.jsp?urltype=news.NewsContentUrl&wbtreeid=1222&wbnewsid=11897
        【5】2022-09-27 关于2022年普通话水平测试工作延期到本学期举办的通知 https://jwc.sjtu.edu.cn/info/1222/11894.htm

# 某时刻bot检测到教务处通知更新
bot> ${教务处通知的图片}
```

图片展示：

![](../../images/plugins/jwc.png)

## 3. 代码分析

```python
from utils.standardPlugin import StandardPlugin, Any, Union, PluginGroupManager
from utils.responseImage import *
import requests
from bs4 import BeautifulSoup as BS
from utils.basicEvent import *
from utils.basicConfigs import *
from threading import Timer
from pathlib import Path
import json
from datetime import datetime
import qrcode
def getSjtuGk():
    """交大信息公开网"""
    html = requests.get('https://gk.sjtu.edu.cn').text
    html = BS(html, 'lxml')
    news = html.find(class_='new-ncon').find_all('li')
    result = []
    for n in news:
        category = n.i.contents[0]
        link = n.a.get('href')
        if link[0] == '/':
            link = 'https://gk.sjtu.edu.cn'+link
        title = n.a.contents[0]
        result.append({
            'category': category,
            'link': link,
            'title': title
        })
    return result
def getSjtuNews():
    """交大新闻网"""
    html = requests.get('https://news.sjtu.edu.cn/jdyw/index.html').text
    html = BS(html, 'lxml')
    news = html.find('div', class_='list-card-h').find_all('li', class_='item')
    result = []
    for n in news:
        card = n.find('a', class_='card')
        link =  card.get('href')
        if link[0] == '/':
            link = 'https://news.sjtu.edu.cn' +link
        imgLink = card.find('img').get('src')
        if imgLink[0] == '/':
            imgLink = 'https://news.sjtu.edu.cn' + imgLink
        title = card.find('p', class_='dot').contents[0]
        detail = card.find('div', class_='des dot').contents[0]
        about = card.find('div', class_='time')
        time = about.find('span').contents[0]
        source = about.find('div', class_='source').p.contents[0]
        result.append({
            'title': title,
            'link': link,
            'imgLink': imgLink,
            'detail': detail,
            'time': time,
            'source': source
        })
    return result
def drawSjtuNews():
    a = ResponseImage(title='交大新闻', 
    titleColor=PALETTE_SJTU_RED, 
    primaryColor=PALETTE_SJTU_RED, 
    footer='update at %s'%datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M"),
    layout='normal')
    for news in sorted(getSjtuNews(), key=lambda x: x['time'], reverse=True):
        a.addCard({
            'style': 'normal',
            'title': news['title'],
            'keyword': news['source'] + '  ' + news['time'],
            'body': news['detail'],
            'icon': news['imgLink']
        })
    a.generateImage(os.path.join(SAVE_TMP_PATH, 'sjtu_news.png'))

def getJwc():
    page = str(requests.get('https://jwc.sjtu.edu.cn/xwtg/tztg.htm').content, 'utf-8')
    page = BS(page, 'lxml')
    news = page.find(class_='Newslist').ul.find_all(class_='clearfix')
    newsList = []
    for n in news:
        sj = n.find(class_='sj')
        year, month = sj.p.contents[0].split('.')
        day = sj.h2.contents[0]
        content = n.find(class_='wz')
        title:str = content.h2.contents[0]
        link:str = content.a.get('href').replace('..', 'https://jwc.sjtu.edu.cn')
        detail:str = content.p.contents[0]
        newsList.append({
            'year': year,
            'month': month,
            'day': day,
            'title': title,
            'detail': detail,
            'link': link,
        })
    return newsList

class GetJwc(StandardPlugin): 
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg=='-jwc'
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        jwc = sorted(getJwc(), key=lambda x: '%s-%s-%s'%(x['year'], x['month'], x['day']), reverse=True)
        jwcStr = ""
        idx = 1
        for j in jwc[:5]:
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
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg=='-sjtu news'
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        pic_path = os.path.join(SAVE_TMP_PATH, 'sjtu_news.png')
        if not Path(pic_path).is_file():
            drawSjtuNews()
        send(target, f'[CQ:image,file=files:///{ROOT_PATH}/{pic_path},id=40000]', data['message_type'])
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

class JwcGroup(PluginGroupManager):
    def __init__(self,):
        super().__init__([GetJwc(), GetSjtuNews()], 'jwc')
        self.checkTimer = Timer(20,self.updateAndCheck)
        self.checkTimer.start()
    def updateAndCheck(self, ):
        self.checkTimer.cancel()
        self.checkTimer = Timer(180,self.updateAndCheck)
        self.checkTimer.start()
        drawSjtuNews()
        noticelist = getJwc()
        exact_path=(f'data/jwc.json')
        if not Path(exact_path).is_file():
            Path(exact_path).write_text(r'[]')
        url_list = json.load(open(exact_path, 'r'))
        for j in noticelist:
            if j['link'] not in url_list:
                url_list.append(j['link'])
                for group_id in APPLY_GROUP_ID:
                    if self.queryEnabled(group_id):
                        pic = DrawNoticePIC(j)
                        send(group_id, '已发现教务通知更新:\n【'+j['title']+'】\n'+j['link'])
                        send(group_id, f'[CQ:image,file=files:///{ROOT_PATH}/{pic},id=40000]')
        with open(exact_path, 'w') as f:
            json.dump(url_list, f, indent=4)

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

```