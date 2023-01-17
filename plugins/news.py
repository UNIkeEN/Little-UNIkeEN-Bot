import requests
from lxml import etree
from PIL import Image, ImageDraw, ImageFont
import datetime
from pathlib import Path
import re
from typing import Union, Any
from utils.basicEvent import *
from utils.basicConfigs import *
from utils.standardPlugin import StandardPlugin

TXT_ONELINE_SIZE=745

class ShowNews(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return (msg in ['每日新闻','新闻'])
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        ret = get_news()
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        if ret=="err 0":
            send(target, "获取失败\n新闻源尚未更新本日新闻", data['message_type'])
        else:
            newsPicPath = ret if os.path.isabs(ret) else os.path.join(ROOT_PATH, ret)
            send(target, f'[CQ:image,file=files://{newsPicPath},id=40000]', data['message_type'])
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
def get_news():
    #建议是生成图片宽度-两侧边距-抖动
    today_str=str(datetime.date.today())
    newsPicPath = os.path.join(SAVE_TMP_PATH, f'{today_str}_news.png')
    if Path(newsPicPath).is_file(): #今日已更新则返回
        return newsPicPath
    headers={
        'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.0.0 Safari/537.36'
    }
    url = 'https://www.liulinblog.com/kuaixun'
    req = requests.get(url=url,headers=headers)
    if req.status_code != requests.codes.ok:
        warning("news api failed in news.py")
        return "err 0"
    page_text = req.text
    tree = etree.HTML(page_text)
    img_url = tree.xpath('//div[@class="col-lg-12"]//a[@target="_blank"]/@href')[0]
    detail_page_text = requests.get(url=img_url,headers=headers).text
    newtree = etree.HTML(detail_page_text)
    title = newtree.xpath('//h1[@class="entry-title"]/text()')[0]

    # 判断是否当日更新
    news_day=int((re.findall("月(.*?)日",title))[0])
    if news_day != int(datetime.date.today().day):
        return "err 0"

    news = newtree.xpath('//div[@class="entry-content u-text-format u-clearfix"]//p/text()')
    #news[0] = title
    total = title
    for new in news[:-1]:
        total = total+new.strip()
        total = total+'\n'
    total=total.replace('https://www.liulinblog.com/','',1)
    total=total.replace('，在这里每天60秒读懂世界！','\n',1)
    return draw_news_card(total)

def draw_news_card(text):
    today_str=str(datetime.date.today())
    txt_line=""
    txt_parse=[]
    for word in text:
        if txt_line=="" and word in ['，','；','。','、','"','：']: #避免标点符号在首位
            txt_parse[-1]+=word
            continue
        
        txt_line+=word
        if word=='\n':
            if txt_line !='\n':
                txt_parse.append(txt_line)
            txt_parse.append("-sep line-")
            txt_line=""
            continue
        if font_hywh_85w_ms.getsize(txt_line)[0]>TXT_ONELINE_SIZE:
            txt_parse.append(txt_line)
            txt_line=""
    if txt_line!="":
        txt_parse.append(txt_line)
    width=880
    i,j=0,0
    for one_line in txt_parse:
        if one_line=="-sep line-":
            j+=1
            continue
        i+=1
    height=250+i*45+j*20
    img = Image.new('RGBA', (width, height), (46, 192, 189, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 120, width, height), fill=(255, 255, 255, 255))
    draw.text((width-300,40), "每日新闻", fill=(255,255,255,255), font=font_hywh_85w)
    draw.text((width-120,44), "LITTLE\nUNIkeEN", fill=(255,255,255,255), font=font_syht_m)
    i,j=0,0
    for one_line in txt_parse:
        if one_line=="-sep line-":
            j+=1
            continue
        draw.text((60,150+i*45+j*20), one_line, fill=(0,0,0,255), font=font_hywh_85w_ms)
        i+=1
    draw.text((30,height-78),'来源:澎湃、人民日报、腾讯新闻、网易新闻、新华网、中国新闻网', fill=(175,175,175,255), font=font_syht_m)
    draw.text((30,height-48),'A plugin by 北极づ莜蓝, made for Little-UNIkeEN-Bot', fill=(175,175,175,255), font=font_syht_m)

    save_path = os.path.join(SAVE_TMP_PATH, f'{today_str}_news.png')
    img.save(save_path)
    return save_path
