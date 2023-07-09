from PIL import Image, ImageDraw, ImageFont
import random
import requests
from datetime import datetime
import json
from io import BytesIO
from threading import Timer, Semaphore
import mysql.connector
from utils.configAPI import getPluginEnabledGroups
from pymysql.converters import escape_string
from typing import Union, Any
from utils.basicEvent import *
from utils.basicConfigs import *
from utils.standardPlugin import StandardPlugin, PluginGroupManager, ScheduleStandardPlugin
from utils.accountOperation import get_user_coins, update_user_coins

CMD_LOTTERY=['祈愿','祈愿帮助']
PRIZE_NUM=[0,30,600,5000]
PRICE_NUM=100
HELP_LOTTERY=(f"""【祈愿帮助】
祈愿 {PRICE_NUM}💰/次
请发送 '祈愿 数字'，数字部分需为3个1-10之间的不重复数字
系统会自动按从小到大排列并按位置匹配，
21时，神明将默念三个数字，数字有对应者将得到神明的认可，
按所中个数1-3分别赠予{PRIZE_NUM[1:]}💰赐礼""")
def createLotterySql():
    mydb = mysql.connector.connect(**sqlConfig)
    mycursor = mydb.cursor()
    mydb.autocommit = True
    mycursor.execute("""create table if not exists `BOT_DATA`.`lotteries`(
        `id` bigint unsigned not null auto_increment,
        `timestp` timestamp default null,
        `record` text default null, 
        primary key (`id`)
    )charset=utf8mb4, collate=utf8mb4_unicode_ci""")
class LotteryReminder(ScheduleStandardPlugin):
    s = Semaphore()
    def __init__(self) -> None:
        if LotteryReminder.s.acquire(blocking=False):
            self.schedule(hour=20, minute=50)
    def tick(self) -> None:
        for group_id in getPluginEnabledGroups('lottery'):
            send(group_id, '🌈🎫本轮祈愿还有10分钟公布~\n - 关于玩法，请发送【祈愿帮助】')

class _lottery(ScheduleStandardPlugin):
    monitorSemaphore = Semaphore()
    def __init__(self):
        self.reminder = LotteryReminder()
        if _lottery.monitorSemaphore.acquire(blocking=False):
            self.schedule(hour=21)

    def buyLottery(self,qq, msg):
        if get_user_coins(qq)<PRICE_NUM:
            return "金币不足"
        msg_split=msg.split()
        num_list=[]
        if len(msg_split)!=4:
            return 
        for i in range(1,4):
            try:
                tmp=int(msg_split[i])
                if tmp<=0 or tmp>10:
                    return "号码需要为1-10之间的数字！"
                if tmp in num_list:
                    return "号码不能有重复喔"
                num_list.append(tmp)
            except:
                return 
        num_list.sort()
        new_lot=json.dumps({'qq':qq, 'num_list':num_list, 'prize':0})
        new_lot=escape_string(new_lot)
        # lot_base.append(new_lot)
        # with open(self.data_path, "w") as f2:
        #     json.dump(lot_base, f2, indent=4)
        # f2.close()
        try:
            mydb = mysql.connector.connect(**sqlConfig)
            mycursor = mydb.cursor()
            now = datetime.now()
            now = now.strftime("%Y-%m-%d %H:%M:%S")
            mycursor.execute(f"INSERT INTO BOT_DATA.lotteries (timestp, record) VALUES ('{now}', '{new_lot}')")
            mydb.commit()
            print("[LOG] Insert Lottery: Done!")
        except mysql.connector.errors.DatabaseError as e: 
            print(e)
        update_user_coins(qq,-PRICE_NUM, '祈愿')
        return (f"祈愿成功！花费【{PRICE_NUM}】💰，剩余【{get_user_coins(qq)}】💰")

    def tick(self): # 开奖
        key_list = sorted(random.sample(range(1, 11), 3))

        mydb = mysql.connector.connect(**sqlConfig)
        mycursor = mydb.cursor()
        mycursor.execute("SELECT record FROM BOT_DATA.lotteries")
        lot_base=list(mycursor)

        win_list=[]
        for _record in lot_base:
            record = json.loads(_record[0])
            num_in = 0
            for i in range(3):
                if key_list[i]==record['num_list'][i]:
                    num_in+=1
            record['prize']=num_in
            if num_in>0:
                win_list.append(record)
                update_user_coins(record['qq'], PRIZE_NUM[num_in], '祈愿成真')
        mycursor.execute("TRUNCATE TABLE BOT_DATA.lotteries;")
        win_list = sorted(win_list,key=lambda x:x['prize'],reverse=True)
        card_path=self.make_card(key_list, win_list)
        r_path=os.path.dirname(os.path.realpath(__file__))
        pic_path=(f'file:///{r_path}/'[:-8]+card_path)
        for group_id in getPluginEnabledGroups('lottery'):
            send(group_id, f'[CQ:image,file={pic_path}]')
        
    def make_card(self, key_list, win_list):
        BACK_CLR = {'r':(255, 232, 236, 255),'g':(219, 255, 228, 255),'h':(234, 234, 234, 255),'o':(254, 232, 199, 255)}
        FONT_CLR = {'r':(221, 0, 38, 255),'g':(0, 191, 48, 255),'h':(64, 64, 64, 255),'o':(244, 149 ,4, 255)}
        TXT_CLASS = ['','三','二','一']
        height=570+150*(len(win_list)-(1 if len(win_list)!=0 else 0))+(90 if len(win_list)!=0 else 0)
        width=840
        img = Image.new('RGBA', (width, height), (244, 149 ,4, 255))
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, 120, width, height), fill=(255, 255, 255, 255))
        draw.text((width-230,40), "祈愿", fill=(255,255,255,255), font=font_hywh_85w)
        draw.text((width-120,44), "LITTLE\nUNIkeEN", fill=(255,255,255,255), font=font_syht_m)
        txt_size = draw.textsize('祈愿 - 开奖结果', font=font_hywh_85w)
        draw.text(((width-txt_size[0])/2,180), "祈愿 - 开奖结果", fill=(0,0,0,255), font=font_hywh_85w)
        rec_width=140
        rec_height=90
        len_win = len(win_list)
        for i in range(3):
            draw.rectangle((180+i*(rec_width+30), 260, 180+i*(rec_width+30)+rec_width, 260+rec_height), fill=BACK_CLR['o'])
            txt_size = draw.textsize(str(key_list[i]), font=font_hywh_85w_l)
            draw.text((180+i*(rec_width+30)+(rec_width-txt_size[0])/2, 275),str(key_list[i]), fill=FONT_CLR['o'], font=font_hywh_85w_l)
        for i in range(len_win):
            # 获取头像
            url_avatar = requests.get('http://q2.qlogo.cn/headimg_dl?dst_uin='+str(win_list[i]['qq'])+'&spec=100')
            img_avatar = Image.open(BytesIO(url_avatar.content)).resize((90,90))
            mask = Image.new('RGBA', (90, 90), color=(0,0,0,0))
            # 圆形蒙版
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0,0, 90, 90), fill=(159,159,160))
            img.paste(img_avatar, (60, 260+150*(i+1)), mask)
            for j in range(3):
                flag = 'g' if win_list[i]['num_list'][j]==key_list[j] else 'r'
                draw.rectangle((180+j*(rec_width+30), 260+150*(i+1), 180+j*(rec_width+30)+rec_width, 260+150*(i+1)+rec_height), fill=BACK_CLR[flag])
                txt_size = draw.textsize(str(win_list[i]['num_list'][j]), font=font_hywh_85w_l)
                draw.text((180+j*(rec_width+30)+(rec_width-txt_size[0])/2, 275+150*(i+1)),str(win_list[i]['num_list'][j]), fill=FONT_CLR[flag], font=font_hywh_85w_l)
            draw.text((width-150, 260+150*(i+1), width, height), f"{TXT_CLASS[win_list[i]['prize']]}等奖", fill=(135,135,135,255), font=font_hywh_85w_s)
            draw.text((width-150, 260+150*(i+1)+40, width, height), f"金币+{PRIZE_NUM[win_list[i]['prize']]}", fill=(135,135,135,255), font=font_hywh_85w_s)
        if len_win==0:
            txt_size = draw.textsize('本期祈愿，没有人得到了神明的认可', font=font_hywh_85w)
            draw.text(((width-txt_size[0])/2,390), "本期祈愿，没有人得到了神明的认可", fill=(145,145,145,255), font=font_hywh_85w)

        draw.text((30,height-48),'发送[祈愿帮助]，查询如何使用本功能', fill=(175,175,175,255), font=font_syht_m)
        save_path=os.path.join(SAVE_TMP_PATH,'lot_draw.png')
        img.save(save_path)
        return save_path


class LotteryPlugin(StandardPlugin):
    warningSemaphore = Semaphore()
    def __init__(self,):
        if LotteryPlugin.warningSemaphore.acquire(blocking=False):
            # warning once
            pass
            # print('注意，开启LotteryPlugin插件有被腾讯封号的风险')
        self.lottery = _lottery()
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return startswith_in(msg,CMD_LOTTERY)
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        if msg=='祈愿帮助':
            send(target, HELP_LOTTERY, data['message_type'])
        else:
            send(target, self.lottery.buyLottery(data['user_id'],msg), data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'LotteryPlugin',
            'description': '祈愿',
            'commandDescription': '祈愿/祈愿帮助',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }