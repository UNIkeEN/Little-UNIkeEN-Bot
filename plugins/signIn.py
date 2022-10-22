from PIL import Image, ImageDraw, ImageFont
import random
import requests
import datetime
from io import BytesIO
import mysql.connector
from typing import Union, Any
from utils.basicEvent import *
from utils.basicConfigs import *
from utils.standardPlugin import StandardPlugin
from utils.accountOperation import get_user_coins, update_user_coins

FORTUNE_TXT = [['r',"大吉"],['r',"中吉"],['r',"小吉"],['g',"中平"],['h',"小凶"],['h',"中凶"],['h',"大凶"],['r',"奆🐔"],['h','奆🐻']]

class SignIn(StandardPlugin): 
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg in ['签到','每日签到','打卡']
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        ret = sign_in(data['user_id'])
        pic_path=(f'file:///{ROOT_PATH}/'+ret)
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        send(target, f'[CQ:image,file={pic_path}]',data['message_type'])
    def getPluginInfo(self,)->Any:
        return {
            'name': 'SignIn',
            'description': '签到',
            'commandDescription': '签到/每日签到/打卡',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
# 绘制签到图
def draw_signinbanner(qq_id, add_coins, now_coins, fortune):
    img = Image.new('RGBA', (720, 480), (random.randint(50,200),random.randint(50,200),random.randint(50,200),255))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 120, 720, 480), fill=(255, 255, 255, 255))
    draw.text((420,40), "每日签到", fill=(255,255,255,255), font=font_hywh_85w)
    draw.text((600,44), "LITTLE\nUNIkeEN", fill=(255,255,255,255), font=font_syht_m)

    # 获取头像
    url_avatar = requests.get(f'http://q2.qlogo.cn/headimg_dl?dst_uin={qq_id}&spec=100')
    img_avatar = Image.open(BytesIO(url_avatar.content)).resize((150,150))
    mask = Image.new('RGBA', (150, 150), color=(0,0,0,0))
    # 圆形蒙版
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0,0, 150, 150), fill=(159,159,160))
    img.paste(img_avatar, (60, 80), mask)
    # ID
    draw.text((250, 150), "id："+str(qq_id), fill=(0, 0, 0, 255), font=font_hywh_85w)
    # 签到及首签徽章
    if add_coins == -1:
        draw.text((60, 280), "今天已经签过到了喔~", fill=(255, 128, 64, 255), font=font_hywh_85w)
    else:
        draw.text((60, 280), f"签到成功，金币+{str(add_coins)}", fill=(34, 177, 76, 255), font=font_hywh_85w)
    draw.text((60, 360), f"当前金币：{str(now_coins)}", fill=(0, 0, 0, 255), font=font_hywh_85w)

    # 运势
    f_type=FORTUNE_TXT[fortune][0]
    draw.rectangle((500,280,660,420),fill=BACK_CLR[f_type])
    draw.text((540,295), '今日运势', fill=FONT_CLR[f_type], font=font_hywh_85w_s)
    if fortune>=7:
        draw.text((525,340), FORTUNE_TXT[fortune][1][0], fill=FONT_CLR[f_type], font=font_hywh_85w_l)
        draw.text((580,350), FORTUNE_TXT[fortune][1][1], fill=FONT_CLR[f_type], font=font_sg_emj)
    else:
        draw.text((525,340), FORTUNE_TXT[fortune][1], fill=FONT_CLR[f_type], font=font_hywh_85w_l)
    
    save_path=(f'{SAVE_TMP_PATH}/{qq_id}_sign.png')
    img.save(save_path)
    return save_path

# 签到
def sign_in(qq_id):
    id=str(qq_id)
    today_str=str(datetime.date.today())
    #first_sign = False
    mydb = mysql.connector.connect(**sqlConfig)
    mycursor = mydb.cursor()
    mycursor.execute(f"SELECT lastSign FROM BOT_DATA.accounts where id={str(id)}")
    result=list(mycursor)
    if len(result)==0:
        mycursor.execute(f"INSERT INTO BOT_DATA.accounts (id, coin, lastSign) VALUES ('{str(id)}', '0', '1980-01-01')")
        mydb.commit()
        last_sign_date = '1980-01-01'
    else:
        last_sign_date = str(result[0][0])
    if last_sign_date !=today_str:
        add_coins = random.randint(50,100)
        fortune = random.randint(0,6)
        update_user_coins(id, add_coins, '签到奖励')
        try:
            mycursor.execute(f"UPDATE BOT_DATA.accounts SET lastSign='{today_str}', fortune='{str(fortune)}' WHERE id='{str(id)}';")
            mydb.commit()
            print("[LOG] Update Sign_Info: Done!")
        except mysql.connector.errors.DatabaseError as e:
            print(e)
        return draw_signinbanner(qq_id, add_coins, get_user_coins(id), fortune)
    else:
        mycursor.execute(f"SELECT fortune FROM BOT_DATA.accounts where id={str(id)}")
        fortune=list(mycursor)[0][0]
        return draw_signinbanner(qq_id, -1, get_user_coins(id), fortune)
