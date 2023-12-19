import os, os.path
import json
import time
from datetime import datetime
from typing import Union, Any, Dict, List
from utils.basicEvent import send, warning, init_image_template, draw_rounded_rectangle
from utils.channelAPI import send_guild_channel_msg
from utils.basicConfigs import *
import requests
from utils.configAPI import getPluginEnabledGroups
from utils.standardPlugin import StandardPlugin, CronStandardPlugin, NotPublishedException
from PIL import Image
from io import BytesIO
from threading import Timer, Semaphore
try:
    from resources.api.dektAPI import getDekt
except ImportError as e:
    raise NotPublishedException(str(e))

DEKT_SOURCE_DIR = os.path.join(ROOT_PATH, 'data/dektSource/')


class SjtuDektMonitor(StandardPlugin, CronStandardPlugin):
    monitorSemaphore = Semaphore()
    def __init__(self) -> None:
        if SjtuDektMonitor.monitorSemaphore.acquire(blocking=False):
            self.start(10, 1790)
            # self.start(10, 600)
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return False
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        return "OK"
    def tick(self) -> None:
        dektSource = getDekt()
        if dektSource == None: return
        fileNames=sorted(os.listdir(DEKT_SOURCE_DIR))
        with open(os.path.join(DEKT_SOURCE_DIR, "dekt-%s.json"%datetime.now().strftime("%Y-%m-%d-%H%M%S")), "w") as f:
            json.dump(dektSource, f, ensure_ascii=False)
        if len(fileNames) == 0:
            return
        try:
            lastData = json.load(open(os.path.join(DEKT_SOURCE_DIR, fileNames[-1]), 'r'))
            currentIDs = set([activity['id'] for activity in dektSource['data']])
            prevIDs = set([activity['id'] for activity in lastData['data']])
            if currentIDs == prevIDs: return
            picPath = NewActlistPic()
            picPath = picPath if os.path.isabs(picPath) else os.path.join(ROOT_PATH, picPath)
            txt = f'已发现第二课堂活动更新:[CQ:image,file=file:///{picPath}]'
            # send_guild_channel_msg(MAIN_GUILD['guild_id'], MAIN_GUILD['channels']['dekt'], txt)
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
    def getPluginInfo(self, )->Dict[str, Any]:
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

def Timestamp2time(timestp:int)->str:
    """convert time stamp in milisecond to string
    @timestp: time stamp in milisecond
    
    @return: timestamp string
    """
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
            txt_size_record = l+170+txt_size[0]
        except:
            enroll_time = '报名时间未知（API返回空值）'
            draw.text((l+150, h+120), enroll_time , fill=(115,115,115,255), font = font_syhtmed_18)
            txt_size_record = l+150
        
        if activity['recruitQty']==0:
            activity['recruitQty']="不限"
        draw.text((l+150, h+160), '招募人数：'+str(activity['recruitQty'])+'  |  组织单位：'+activity['sponsor'][:21], fill=(115,115,115,255), font = font_syhtmed_18)
        if len(activity['sponsor'])>20:
            txt_size=draw.textsize('招募人数：'+str(activity['recruitQty'])+'  |  组织单位：',font=font_syhtmed_18)
            t = activity['sponsor'][21:42]+('...' if len(activity['sponsor'])>=42 else '')
            draw.text((l+150+txt_size[0], h+163+txt_size[1]), t, fill=(115,115,115,255), font = font_syhtmed_18)
        activityCategorya = {'hszl':'红色之旅','ldjy':'劳动教育','zygy':'志愿公益','wthd':'文体活动','kjcx':'科技创新','jtjz':'讲坛讲座','qt':'  其他  '}.get(activity['activityCategorya'], '  未知  ')
        draw.text((l+38, h+160), activityCategorya, fill=(115,115,115,255),font=font_syhtmed_18)
        try:
            activeDurationDesc = activity['activeDurationDesc']
            activeDurationDesc = 0 if activeDurationDesc == None else float(activeDurationDesc)
            activeDurationDesc = '学时：{:.0f}分钟'.format(activeDurationDesc)
        except Exception as e:
            print(e)
            activeDurationDesc = '学时：未知'
        draw.text((txt_size_record-10, h+80), activeDurationDesc, fill=(115,115,115,255),font=font_syhtmed_18)
        h+=240
    txt_size = draw.textsize(f'活动列表更新时间 {rettime[:10]} {rettime[11:13]}:{rettime[13:15]}:{rettime[15:]}',font=font_syhtmed_18)
    draw.text((width/2-txt_size[0]/2, height-85), f'活动列表更新时间 {rettime[:10]} {rettime[11:13]}:{rettime[13:15]}:{rettime[15:]}', fill=(115,115,115,255), font = font_syhtmed_18) 
    save_path= os.path.join(SAVE_TMP_PATH, 'dekt.png')
    img.save(save_path)
    return save_path
