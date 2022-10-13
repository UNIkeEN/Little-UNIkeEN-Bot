from PIL import Image, ImageDraw, ImageFont
import random
import requests
from datetime import datetime
import json
from io import BytesIO
from threading import Timer
import mysql.connector
from pymysql.converters import escape_string
from typing import Union, Any
from utils.basicEvent import *
from utils.basicConfigs import *
from utils.standardPlugin import StandardPlugin, PluginGroupManager
from utils.accountOperation import get_user_coins, update_user_coins

CMD_LOTTERY=['购买彩票','买彩票','彩票帮助']
PRIZE_NUM=[0,10,200,1200]
PRICE_NUM=30
HELP_LOTTERY=(f"""彩票帮助
彩票{PRICE_NUM}金币/张
购买彩票请发送 '买彩票 数字'
数字部分需为3个1-10之间的不重复数字
系统会自动按从小到大排列
开奖时按位置匹配，按所中个数1-3分别发放{PRIZE_NUM[1:]}金币奖金
21时开奖，一名用户在一个周期内可以重复购买""")

class _lottery():
    def __init__(self):
        self.timer=Timer(1,self.drawing)
        self.timer.start()

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
        update_user_coins(qq,-PRICE_NUM, '购买彩票')
        return (f"购买成功！扣款【{PRICE_NUM}】金币，剩余金币：【{get_user_coins(qq)}】")

    def drawing(self): # 判断时间并开奖
        #global auto_timer
        now_time = datetime.now()
        h_m = datetime.strftime(now_time,'%H:%M')
        self.timer.cancel()
        self.timer=Timer(60,self.drawing)
        self.timer.start()
        #print(h_m)
        if h_m in ['20:50']:
            for group_id in APPLY_GROUP_ID:
                if check_config(group_id,'Lottery'):
                    send(group_id, '🌈🎫本轮彩票还有10分钟开奖~\n - 关于玩法，请发送【彩票帮助】')
        if h_m in ['21:00']:
        #if True:
            key_list=[]
            win_list=[]
            for i in range(3):
                while True:
                    tmp=random.randint(1,10)
                    #print(str(tmp)+';')
                    if tmp not in key_list:
                        key_list.append(tmp)
                        break
            key_list.sort()
            #print(key_list)
            mydb = mysql.connector.connect(**sqlConfig)
            mycursor = mydb.cursor()
            mycursor.execute("SELECT record FROM BOT_DATA.lotteries")
            lot_base=list(mycursor)
            for _record in lot_base:
                record = json.loads(_record[0])
                num_in = 0
                for i in range(3):
                    if key_list[i]==record['num_list'][i]:
                        num_in+=1
                record['prize']=num_in
                if num_in>0:
                    win_list.append(record)
                    update_user_coins(record['qq'], PRIZE_NUM[num_in], '彩票中奖')
            mycursor.execute("TRUNCATE TABLE BOT_DATA.lotteries;")
            #mydb.commit()
            win_list = sorted(win_list,key=lambda x:x['prize'],reverse=True)
            card_path=self.make_card(key_list, win_list)
            r_path=os.path.dirname(os.path.realpath(__file__))
            pic_path=(f'file:///{r_path}/'[:-8]+card_path)
            for group_id in APPLY_GROUP_ID:
                #print(check_config(group_id, 'Lottery'))
                if check_config(group_id, 'Lottery'):
                    send(group_id, f'[CQ:image,file={pic_path}]')
        return
        
    def make_card(self, key_list, win_list):
        BACK_CLR = {'r':(255, 232, 236, 255),'g':(219, 255, 228, 255),'h':(234, 234, 234, 255),'o':(254, 232, 199, 255)}
        FONT_CLR = {'r':(221, 0, 38, 255),'g':(0, 191, 48, 255),'h':(64, 64, 64, 255),'o':(244, 149 ,4, 255)}
        TXT_CLASS = ['','三','二','一']
        height=570+150*(len(win_list)-(1 if len(win_list)!=0 else 0))+(90 if len(win_list)!=0 else 0)
        width=840
        img = Image.new('RGBA', (width, height), (244, 149 ,4, 255))
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, 120, width, height), fill=(255, 255, 255, 255))
        draw.text((width-260,40), "三色彩", fill=(255,255,255,255), font=font_hywh_85w)
        draw.text((width-120,44), "LITTLE\nUNIkeEN", fill=(255,255,255,255), font=font_syht_m)
        txt_size = draw.textsize('三色彩 - 开奖结果', font=font_hywh_85w)
        draw.text(((width-txt_size[0])/2,180), "三色彩 - 开奖结果", fill=(0,0,0,255), font=font_hywh_85w)
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
            txt_size = draw.textsize('本期彩票无人中奖', font=font_hywh_85w)
            draw.text(((width-txt_size[0])/2,390), "本期群内无人中奖", fill=(145,145,145,255), font=font_hywh_85w)

        draw.text((30,height-48),'发送[彩票帮助]，查询如何使用本功能', fill=(175,175,175,255), font=font_syht_m)
        save_path=os.path.join(SAVE_TMP_PATH,'lot_draw.png')
        img.save(save_path)
        return save_path


class LotteryPlugin(StandardPlugin):
    def __init__(self,):
        self.lottery = _lottery()
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return startswith_in(msg,CMD_LOTTERY)
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        if data['message_type']=='group' and not check_config(data['group_id'],'Lottery'):
            send(target, TXT_PERMISSION_DENIED)
            return "OK"
        if msg=='彩票帮助':
            send(target, HELP_LOTTERY, data['message_type'])
        else:
            send(target, self.lottery.buyLottery(data['user_id'],msg), data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'LotteryPlugin',
            'description': '彩票',
            'commandDescription': '购买彩票/买彩票',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }