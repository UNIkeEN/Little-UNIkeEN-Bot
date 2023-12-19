from PIL import Image, ImageDraw, ImageFont
import random
import requests
import datetime
from io import BytesIO
from utils.sqlUtils import newSqlSession
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
        picPath = sign_in(data['user_id'])
        picPath = picPath if os.path.isabs(picPath) else os.path.join(ROOT_PATH, picPath)
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        send(target, f'[CQ:image,file=file:///{picPath}]',data['message_type'])
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
    width=720
    height=800
    r = random.randint(50,150)
    g = random.randint(50,150)
    b = random.randint(50,150)
    img, draw, h=init_image_template("每日签到",width, height, (r,g,b,255))
    # img = Image.new('RGBA', (720, 480), (random.randint(50,200),random.randint(50,200),random.randint(50,200),255))
    # draw = ImageDraw.Draw(img)
    # draw.rectangle((0, 120, 720, 480), fill=(255, 255, 255, 255))
    # draw.text((420,40), "每日签到", fill=(255,255,255,255), font=font_hywh_85w)
    # draw.text((600,44), "LITTLE\nUNIkeEN", fill=(255,255,255,255), font=font_syht_m)
    # 获取头像
    url_avatar = requests.get(f'http://q2.qlogo.cn/headimg_dl?dst_uin={qq_id}&spec=100')
    img_avatar = Image.open(BytesIO(url_avatar.content)).resize((150,150))
    mask = Image.new('RGBA', (150, 150), color=(0,0,0,0))
    h+=130
    l=60
    # 蒙版
    mask_draw = ImageDraw.Draw(mask)
    mask = draw_rounded_rectangle(mask, 0, 0, 150, 150, (159,159,160))
    img.paste(img_avatar, (l, h), mask)
    # ID
    img = draw_rounded_rectangle(img, l+180, h, width-60,h+150, (245+10*r//255,245+10*g//255,245+10*b//255,255))
    draw.text((l+210, h+35), "id："+str(qq_id), fill=(0, 0, 0, 255), font=font_syhtmed_32)
    font_syhtmed_28 = ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 28)
    # 签到及首签徽章
    if add_coins == -1:
        draw.text((l+210, h+85), f"今日已签  |  当前金币：{str(int(now_coins*100)//100)}", fill=(255, 128, 64, 255), font=font_syhtmed_28)
    else:
        draw.text((l+210, h+85), f"金币+{str(add_coins)}  |  当前金币：{str(int(now_coins*100)//100)}", fill=(34, 177, 76, 255), font=font_syhtmed_28)
    h+=180
    # 运势
    f_type=FORTUNE_TXT[fortune][0]
    # f_type='r'
    img = draw_rounded_rectangle(img, width-220, h, width-60, h+150, fill=BACK_CLR[f_type])
    draw.text((width-180, h+20), '今日运势', fill=FONT_CLR[f_type], font=font_hywh_85w_s)
    # draw.rectangle((500,280,660,420),fill=BACK_CLR[f_type])
    # draw.text((540,295), '今日运势', fill=FONT_CLR[f_type], font=font_hywh_85w_s)
    draw.text((width-195, h+65), FORTUNE_TXT[fortune][1], fill=FONT_CLR[f_type], font=font_hywh_85w_l)

    img = draw_rounded_rectangle(img, 60, h, width-250, h+360, fill=(255,255,255,255))
    # img_tmp=Image.open(IMAGES_PATH+'水源社区.png').resize((45,45))
    # img.paste(img_tmp, (l+15, h+360-60))
    quote = random.choice(QUOTE_LIST)
    txt_size=draw.textsize(quote, font=font_syhtmed_18)
    draw.text((l+15, h+360-33), "疫情文学大赏与短诗大赛节选", fill = (175,175,175,255), font=font_syhtmed_18)
    draw.text((l+25, h+(360-txt_size[1])/2-25), quote, fill = (85,85,85,255), font=font_syhtmed_18)

    font_syst= ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSerifCN-Bold.otf'), 28)
    txt_size=draw.textsize("众志成城", font=font_syst)
    img = draw_rounded_rectangle(img, width-220, h+180, width-60, h+360, fill=(161,34,34,255))
    draw.text((width-220+(160-txt_size[0])/2, h+205), "众志成城", fill=(255,255,255,255),font=font_syst)
    draw.text((width-220+(160-txt_size[0])/2, h+250), "抗击疫情", fill=(255,255,255,255),font=font_syst)
    str1 = '2022-09-13'
    str2 = str(datetime.date.today()) 
    date1=datetime.datetime.strptime(str1[0:10],"%Y-%m-%d")
    date2=datetime.datetime.strptime(str2[0:10],"%Y-%m-%d")
    num=(date2-date1).days+1
    txt_size=draw.textsize(f"DAY {num}", font=font_syst)
    draw.text((width-220+(160-txt_size[0])/2, h+295), f"DAY {num}", fill=(255,255,255,255),font=font_syst)
    save_path=(f'{SAVE_TMP_PATH}/{qq_id}_sign.png')
    img.save(save_path)
    return save_path

# 签到
def sign_in(qq_id):
    id=str(qq_id)
    today_str=str(datetime.date.today())
    #first_sign = False
    mydb, mycursor = newSqlSession()
    mycursor.execute(f"SELECT lastSign FROM `accounts` where id={str(id)}")
    result=list(mycursor)
    if len(result)==0:
        mycursor.execute(f"INSERT INTO `accounts` (id, coin, lastSign) VALUES ('{str(id)}', '0', '1980-01-01')")
        last_sign_date = '1980-01-01'
    else:
        last_sign_date = str(result[0][0])
    if last_sign_date !=today_str:
        add_coins = random.randint(50,100)
        fortune = random.randint(0,3)
        update_user_coins(id, add_coins, '签到奖励')
        try:
            mycursor.execute(f"UPDATE `accounts` SET lastSign='{today_str}', fortune='{str(fortune)}' WHERE id='{str(id)}';")
            print("[LOG] Update Sign_Info: Done!")
        except mysql.connector.errors.DatabaseError as e:
            print(e)
        return draw_signinbanner(qq_id, add_coins, get_user_coins(id), fortune)
    else:
        mycursor.execute(f"SELECT fortune FROM `accounts` where id={str(id)}")
        fortune=list(mycursor)[0][0]
        return draw_signinbanner(qq_id, -1, get_user_coins(id), fortune)

QUOTE_LIST=[
    """在我的窗外，\n\n可以看见路旁有两栋楼，\n\n一栋是B2，\n\n还有一栋也是B2。\n\n  ——ffmplay""",
    "我和她最接近的时候，\n\n我们之间的距离只有0.01公分，\n\n六个小时之后，\n\n我们楼变成了A级\n\n  ——Lindlar7",
    "如果\n\n我有多一张的出楼证\n\n你会不会跟我走\n\n  ——一之山",
    "凡永恒伟大的爱\n\n都要核酸五次 隔离两周 一度阳性\n\n才会重获爱 重新知道生命的价值\n\n  ——一之山",
    """保重。万物都是恶劣的窃贼\n
手机偷走眼睛；口罩偷走了脸\n
高热和肺炎袭来，偷走生命\n
方舱从我身边偷走了你，妈妈\n
我们的笑与哭有人听见吗\n
又是谁从这历史中偷走了我们的三年\n\n  ——小王的奇妙冒险（节选）""",
"自云先世乃秦时次密接，\n\n与妻子邑人来此隔离，\n\n不复出焉，\n\n遂与外人间隔。\n\n问今是何世，\n\n乃不知有汉，无论魏晋。\n\n  ——ColdAir",
"不知道从什么时候开始，\n\n在什么东西上面都会有个日期，\n\n秋刀鱼会过期，肉酱会过期，\n\n连保鲜纸都会过期，\n\n我开始怀疑在这个世界上，\n\n只有封闭的day0是没有标明日期的。\n\n  ——无糖中可少冰",
"堆来枕上愁何状，\n\n江海翻波浪。\n\n夜长天色总难明，\n\n寂寞披衣，\n\n起坐数寒星。\n\n  ——何从",
"他不过是一个自私的男子，\n\n她不过是一个自私的女人。\n\n在这兵荒马乱的时代，\n\n个人主义者是无处容身的，\n\n可是总有地方容得下一对绿码的夫妻。\n\n  ——柏拉图",
"我好想做嘉然小姐的连花清瘟啊。\n\n可是嘉然小姐说她喜欢的是泡腾片，\n\n我哭了 我知道既不是连花清瘟也不是泡腾片的我\n\n为什么要哭。\n\n因为我其实是一盒丽华快餐。\n\n  ——傻篮子",
"世界上只有一种真正的英雄主义，\n\n那就是确诊后依旧热爱生活，\n\n或者是密接隔离后依旧热爱生活。\n\n  ——Lycorisei",
"多年以后，\n\n当我回忆起我的大学生活的时候，\n\n我会骄傲的告诉别人，\n\n我十二天做了九次核酸，\n\n练成了九阴真经。\n\n  ——Lycorisei",
"你知道，有些同学是注定不会关在宿舍里的，\n\n它的每一片羽毛都闪耀着B级楼栋的光辉。\n\nYou know some students \nare not meant to be caged,\n\ntheir feather are just too 'level B'.\n\n  ——东川路第一小菜鸡",
"那么，一栋楼呐，自己就不可以预料，\n\n一栋楼的命运啊，\n\n当然要考虑自我奋斗，\n\n但是也要考虑到历史的行程。\n\n我一栋B2的楼怎么就变成A1了呢。\n\n  ——猛男驾到通通闪开",
"核酸 手机 课本 雨课堂\n\n我有八只手\n\n狂风暴雨 随机应变\n\n早安 早八人\n\n  ——ling羽雨",
"你说解封要来\n\n我等到石楠花开\n\n花香淡淡\n\n（疫）情泪两行也淡淡\n\n我盼解封 万般心酸\n\n  ——今天是芙来day吗",
"瘟癀挟晦黯东川，遏阻春光皂幕前。\n\n栏索震鸣传战角，喉舌啊喝起幡竿。\n\n火灯并举连星宿，荫影杂叠错晕斓。\n\n日月交通驱翳垢，再披晨霞贯明天。\n\n  ——望舒剑鞘",
"人是可以以二氧化碳为生的，\n\n只要被封控。\n\n  ——小黄同学",
"""他说：口罩是欲发声者的锁链\n
是人群的绝症 是权力之莫比乌斯环\n
一面疯狂，一面保守\n
你说：口罩是观点的盔甲\n
是逼仄的现实里最宽敞的自由\n
孕育笼中困兽和它的月\n
一个撕咬理想，一个是理想本身\n
  ———《口罩》""",
"""疫情让一切都变成了正襟危坐地必要\n
诶 人间是由无数个非必要组成的啊\n
  ———《非必要离校（节选）》"""
]