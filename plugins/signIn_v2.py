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
from utils.responseImage_beta import *
from plugins.notPublished.getMddCola import getTea

FORTUNE_TXT = [['r',"大吉"],['r',"中吉"],['r',"小吉"],['g',"中平"],['h',"小赢"],['h',"中赢"],['h',"大赢"]]

class SignIn(StandardPlugin): 
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg in ['签到','每日签到','打卡']
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        picPath = sign_in(data['user_id'])
        picPath = picPath if os.path.isabs(picPath) else os.path.join(ROOT_PATH, picPath)
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        send(target, f'[CQ:image,file=files:///{picPath}]',data['message_type'])
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
def draw_signinbanner(qq_id:int, add_coins, now_coins, fortune):
    SignInCards = ResponseImage(
            titleColor = PALETTE_SJTU_BLUE,
            title = '每日签到',
            layout = 'normal',
            width = 880,
            cardBodyFont= ImageFont.truetype(os.path.join(FONTS_PATH, '汉仪文黑.ttf'), 60),
            cardTitleFont= ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 26),
            cardSubtitleFont= ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 20),
        )

    # 第一段：基本信息+金币情况
    InfoContent = [('title','ID : %d'%(qq_id)),('separator',),]
    # 获取头像
    img_avatar = Image.open(BytesIO(get_avatar_pic(qq_id)))
    # 金币情况
    if add_coins == -1:
        InfoContent.append(('title','今天已经签过到了喔~', PALETTE_SJTU_DARKBLUE))
    else:
        InfoContent.append(('title',f'签到成功，金币+{str(add_coins)}', PALETTE_GREEN))
    InfoContent.append(('title',f'当前金币：{str(now_coins)}', PALETTE_GREY_SUBTITLE))

    SignInCards.addCard(
        ResponseImage.RichContentCard(
            raw_content = InfoContent,
            icon = img_avatar
        )
    )

    # 第二段：运势
    if fortune<=2:
        clr_back, clr_front = PALETTE_LIGHTRED, PALETTE_RED
    elif fortune>=4:
        clr_back, clr_front = PALETTE_GREY_BORDER, PALETTE_GREY_SUBTITLE
    else:
        clr_back, clr_front = PALETTE_LIGHTGREEN, PALETTE_GREEN

    SignInCards.addCard(
        ResponseImage.NoticeCard(
            title = '今日运势',
            titleFontColor = clr_front,
            bodyFontColor = clr_front,
            backColor = clr_back,
            body = FORTUNE_TXT[fortune][1]
        )
    )
    
    # 第三段：雪碧
    status, description = getTea(qq_id)
    if status == False and description == '查询失败':
        SignInCards.addCard(
            ResponseImage.RichContentCard(
                raw_content = [('subtitle', '* 绑定授权码以同步领取麦当劳每日免费雪碧\n发送命令【-icola】查看详情')],
                backColor = PALETTE_GREY_BACK
            )
        )
    elif status == True or description=='当日已领取请明天再来':
        SignInCards.addCard(
            ResponseImage.RichContentCard(
                raw_content = [
                    ('title', f'已成功同步领取今日麦当劳【免费雪碧】！', (35,210,137,255)),
                    ('title','打开麦当劳APP或小程序, 即可看到优惠券~',PALETTE_GREY_SUBTITLE),
                    ('separator',),
                    ('subtitle','技术支持: Teruteru')
                ],
                backColor = (214,255,238,255),
                icon = os.path.join(IMAGES_PATH,'Sprite.png')
            )
        )
    else:
        SignInCards.addCard(
            ResponseImage.RichContentCard(
                raw_content = [
                    ('subtitle', f'* 同步领取麦当劳每日免费雪碧失败\n原因: {description}'),
                    ],
                backColor = PALETTE_GREY_BACK
            )
        )
    
    save_path=os.path.join(SAVE_TMP_PATH, "%d_sign.png"%qq_id)
    SignInCards.generateImage(save_path)
    return save_path

# 签到
def sign_in(qq_id:int):
    id= qq_id if isinstance(qq_id, int) else int(qq_id)
    today_str=str(datetime.date.today())
    #first_sign = False
    mydb = mysql.connector.connect(**sqlConfig)
    mydb.autocommit = True
    mycursor = mydb.cursor()
    mycursor.execute("SELECT lastSign FROM BOT_DATA.accounts where id=%d"%id)
    result=list(mycursor)
    if len(result)==0:
        mycursor.execute("""INSERT INTO BOT_DATA.accounts (id, coin, lastSign) 
            VALUES (%d, '0', '1980-01-01')"""%id)
        last_sign_date = '1980-01-01'
    else:
        last_sign_date = str(result[0][0])
    if last_sign_date !=today_str:
        add_coins = random.randint(50,100)
        fortune = random.randint(0,6)
        update_user_coins(id, add_coins, '签到奖励')
        try:
            mycursor.execute("UPDATE BOT_DATA.accounts SET lastSign='%s', fortune=%d WHERE id=%d;"
                %(escape_string(today_str), fortune, id))
        except mysql.connector.errors.DatabaseError as e:
            warning("sql error in signin: {}".format(e))
        return draw_signinbanner(id, add_coins, get_user_coins(id), fortune)
    else:
        mycursor.execute("SELECT fortune FROM BOT_DATA.accounts where id=%d"%id)
        fortune=list(mycursor)[0][0]
        return draw_signinbanner(id, -1, get_user_coins(id), fortune)
