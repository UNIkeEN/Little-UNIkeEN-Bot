import os, os.path
import json
import time
from datetime import datetime
from typing import Union, Any
from utils.basicEvent import send, warning, init_image_template, draw_rounded_rectangle
from utils.basicConfigs import *
import requests
from utils.configAPI import getPluginEnabledGroups
from utils.standardPlugin import StandardPlugin, CronStandardPlugin, NotPublishedException
from PIL import Image
from io import BytesIO
from threading import Timer, Semaphore
try:
    from selenium import webdriver
    from selenium.webdriver import ChromeOptions
    from browsermobproxy import Server
except ImportError as e:
    raise NotPublishedException(str(e))

DEKT_SOURCE_DIR = os.path.join(ROOT_PATH, 'data/dektSource/')
BROWSERMOB_SERVER_PATH = '/root/dektFetcher/browsermob-proxy-2.1.4/bin/browsermob-proxy'
if not os.path.isfile(BROWSERMOB_SERVER_PATH):
    raise NotPublishedException("browsermob-proxy尚未安装")
if not isinstance(JAC_COOKIE, str) or len(JAC_COOKIE) < 10:
    raise NotPublishedException("JAC_COOKIE尚未填写")
def DownloadActlist():
    server = Server(BROWSERMOB_SERVER_PATH)
    server.start()
    proxy = server.create_proxy()
    edgeOptions = ChromeOptions()
    edgeOptions.add_argument('ignore-certificate-errors')
    edgeOptions.add_argument('--headless')
    edgeOptions.add_argument('--no-sandbox')
    edgeOptions.add_argument(f'--proxy-server={proxy.proxy}')
    proxy.new_har("dekt", options={'captureHeaders': True, 'captureContent': True})
    def parseCookie(cookieStr: str):
        cookies = []
        cookieStr = cookieStr.split(';')
        for cookie in cookieStr:
            cookie = cookie.strip().split('=')
            cookies.append({
                'domain': '.sjtu.edu.cn',
                'httpOnly': False,
                'name': cookie[0],
                'path': '/',
                'secure': False,
                'value': cookie[1]
            })
        return cookies
    driver=webdriver.Chrome(options=edgeOptions)
    driver.get("https://jaccount.sjtu.edu.cn")
    time.sleep(5)
    cookies = parseCookie(JAC_COOKIE)
    for cookie in cookies:
        if 'expiry' in cookie:
            del cookie['expiry']
        driver.add_cookie(cookie)
    driver.get("https://dekt.sjtu.edu.cn/h5/")
    time.sleep(7)
    result = proxy.har
    #print(result)
    for entry in result['log']['entries']:
        _url = entry['request']['url']
        # 根据URL找到数据接口
        if "api/wmt/secondclass/fmGetNewestActivityList" in _url:
            _response = entry['response']
            _content = _response['content']['text']
            # 获取接口返回内容
            with open(os.path.join(DEKT_SOURCE_DIR, "dekt-%s.json"%datetime.now().strftime("%Y-%m-%d-%H%M%S")), "w") as f:
                f.write(_content)
    server.stop()
    driver.close()
    driver.quit()
    os.system("kill `ps -ef | grep browsermob | awk 'NR==1{print $2}'`")

class SjtuDektMonitor(StandardPlugin, CronStandardPlugin):
    monitorSemaphore = Semaphore()
    def __init__(self) -> None:
        if SjtuDektMonitor.monitorSemaphore.acquire(blocking=False):
            self.start(10, 1790)
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return False
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        return "OK"
    def tick(self) -> None:
        DownloadActlist()
        fileName=sorted(os.listdir(DEKT_SOURCE_DIR))[-2:]
        if len(fileName) < 2:
            return
        try:
            data_1 = json.load(open(os.path.join(DEKT_SOURCE_DIR, fileName[0]), 'r'))
            data_2 = json.load(open(os.path.join(DEKT_SOURCE_DIR, fileName[1]), 'r'))
            if data_1['data'][0]['id'] != data_2['data'][0]['id']:
                picPath = NewActlistPic()
                picPath = picPath if os.path.isabs(picPath) else os.path.join(ROOT_PATH, picPath)
                txt = f'已发现第二课堂活动更新:[CQ:image,file=file:///{picPath}]'
                for group_id in getPluginEnabledGroups('dekt'):
                    send(group_id, txt, 'group')
                    time.sleep(1)
        except json.JSONDecodeError as e:
            warning("dekt json parse error {}".format(e))
        except KeyError as e:
            warning("dekt key error: {}".format(e))
        except BaseException as e:
            warning("dekt error: {}".format(e))
    def getPluginInfo(self, )->Any:
        return {
            'name': 'SjtuDektMonitor',
            'description': '第二课堂更新广播',
            'commandDescription': '[-grpcfg驱动]',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.4',
            'author': 'Unicorn',
        }

class SjtuDekt(StandardPlugin): 
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg == '-dekt'
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        picPath = NewActlistPic()
        picPath = picPath if os.path.isabs(picPath) else os.path.join(ROOT_PATH, picPath)
        send(target, '[CQ:image,file=file:///%s]'%(picPath), data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'SjtuDekt',
            'description': '第二课堂',
            'commandDescription': '-dekt',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }

def Timestamp2time(timestp):
    time_local = time.localtime(float(timestp/1000))
    dt = time.strftime("%Y-%m-%d %H:%M:%S",time_local)
    return str(dt)

def getNewestDektJSON():
    fileName=sorted(os.listdir(DEKT_SOURCE_DIR))[-1]
    try:
        data = json.load(open(os.path.join(DEKT_SOURCE_DIR, fileName), 'r'))
        return data['data'], fileName[5:22]
    except json.JSONDecodeError as e:
        warning("dekt json decode error: {}".format(e))
    except BaseException as e:
        warning("exception in dekt getNewestDektJSON: {}".format(e))

def NewActlistPic():
    nowtime = time.time()*1000
    actlist, rettime = getNewestDektJSON()
    width=880
    height=len(actlist)*240+250
    img, draw, h = init_image_template('第二课堂·最新活动', width, height, (39,82,163,255))
    h+=130
    for activity in actlist:
        img = draw_rounded_rectangle(img, x1=60, y1=h, x2=width-60 ,y2=h+210, fill=(255,255,255,255))
        l = 60
        url_avatar = requests.get(activity['activityPicurl'])
        if url_avatar.status_code != requests.codes.ok:
            img_avatar = None
        else:
            img_avatar = Image.open(BytesIO(url_avatar.content)).resize((90,90))
        img.paste(img_avatar, (l+30, h+30))
        txt_size = draw.textsize(activity['activityName'], font = font_syhtmed_24)
        act_txt = ""
        if txt_size[0]>(width-l-270):
            for t in activity['activityName']:
                txt_size_2 = draw.textsize(act_txt+t, font = font_syhtmed_24)
                if txt_size_2[0]>(width-l-270):
                    act_txt+='...'
                    break
                act_txt+=t
        else:
            act_txt = activity['activityName']
        draw.text((l+150, h+30), act_txt, fill=(0,0,0,255), font = font_syhtmed_24)
        draw.text((l+150, h+80), '活动时间：'+Timestamp2time(activity['activeStartTime'])+' ~ '+Timestamp2time(activity['activeEndTime']), fill=(115,115,115,255), font = font_syhtmed_18)
        try:
            clr = 'o' if nowtime < activity['enrollStartTime'] else 'g'
            # print(nowtime,' ' , activity['enrollStartTime'])
            clr = 'h' if nowtime > activity['enrollEndTime'] else clr
            flag_txt = '报名未开始' if clr=='o' else '报名进行中'
            flag_txt = '报名已结束' if clr=='h' else flag_txt
            enroll_time = '报名时间：'+Timestamp2time(activity['enrollStartTime'])+' ~ '+Timestamp2time(activity['enrollEndTime'])
            draw.text((l+150, h+120), enroll_time , fill=(115,115,115,255), font = font_syhtmed_18)
            txt_size = draw.textsize(enroll_time, font= font_syhtmed_18)
            txt_size_2 = draw.textsize(flag_txt, font= font_syhtmed_18)
            img = draw_rounded_rectangle(img, x1=l+160+txt_size[0], y1=h+110, x2=l+180+txt_size[0]+txt_size_2[0] ,y2=h+txt_size_2[1]+130, fill=BACK_CLR[clr])
            draw.text((l+170+txt_size[0], h+120), flag_txt, fill=FONT_CLR[clr], font=font_syhtmed_18)
        except:
            enroll_time = '报名时间未知（API返回空值）'
            draw.text((l+150, h+120), enroll_time , fill=(115,115,115,255), font = font_syhtmed_18)
            pass
        
        if activity['recruitQty']==0:
            activity['recruitQty']="不限"
        draw.text((l+150, h+160), '招募人数：'+str(activity['recruitQty'])+'  |  组织单位：'+activity['sponsor'][:21], fill=(115,115,115,255), font = font_syhtmed_18)
        if len(activity['sponsor'])>20:
            txt_size=draw.textsize('招募人数：'+str(activity['recruitQty'])+'  |  组织单位：',font=font_syhtmed_18)
            t = activity['sponsor'][21:42]+('...' if len(activity['sponsor'])>=42 else '')
            draw.text((l+150+txt_size[0], h+163+txt_size[1]), t, fill=(115,115,115,255), font = font_syhtmed_18)
        h+=240
    txt_size = draw.textsize(f'活动列表更新时间 {rettime[:10]} {rettime[11:13]}:{rettime[13:15]}:{rettime[15:]}',font=font_syhtmed_18)
    draw.text((width/2-txt_size[0]/2, height-85), f'活动列表更新时间 {rettime[:10]} {rettime[11:13]}:{rettime[13:15]}:{rettime[15:]}', fill=(115,115,115,255), font = font_syhtmed_18) 
    save_path= os.path.join(SAVE_TMP_PATH, 'dekt.png')
    img.save(save_path)
    return save_path