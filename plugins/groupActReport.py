from utils.basicConfigs import ROOT_PATH, SAVE_TMP_PATH, sqlConfig
from utils.basicEvent import send, warning, startswith_in, get_avatar_pic
from typing import Union, Tuple, Any, List
from utils.standardPlugin import StandardPlugin
from PIL import Image, ImageDraw, ImageFont
import mysql.connector
from utils.responseImage_beta import *
import matplotlib.pyplot as plt
import datetime
from copy import deepcopy
from io import BytesIO
import re

class ActReportPlugin(StandardPlugin): # 查询当前金币
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg == '-myact' and data['message_type'] == 'group'
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        imgPath = getMyActivity(data['user_id'], data['group_id'])
        imgPath = imgPath if os.path.isabs(imgPath) else os.path.join(ROOT_PATH, imgPath)
        send(data['group_id'], '[CQ:image,file=files://%s]'%imgPath, data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'ActReport',
            'description': '我的水群报告',
            'commandDescription': '-myact',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
    
def getMyActivity(user_id, group_id):
    messageNumber = 0
    messageWithBotNumber = 0
    messageDescript = ''
    messageMedal = []
    messageWithBotMedal = []
    messageImgEmjMedal = []
    try:
        mydb = mysql.connector.connect(**sqlConfig)
        mycursor = mydb.cursor()
        mycursor.execute("SELECT time, message FROM BOT_DATA.messageRecord where user_id=%d and group_id=%d"%(user_id, group_id))
        result=list(mycursor)
        # 消息数量
        messageNumber = len(result)
        # 消息-时间图
        time_mes = {}
        time_meswithbot = {}
        time_meswithimgemoji = {} #图片类动画表情
        st:datetime.datetime = result[0][0]
        et:datetime.datetime = result[-1][0]
        for time, message in result:
            time: datetime.datetime
            message: str
            message = message.strip()
            t = time.strftime('%Y-%m-%d')
            y = time_mes.get(t,0)
            y += 1
            time_mes[t] = y
            if startswith_in(message.strip(),['-ddl','-canvas','签到','祈愿','-help','-st','-lib','-hs','-mdd','-jwc','-dekt','-mc','-sjmc','-fdc','-tjmc','-mclive','-sjmclive','-fdmclive','小马，','小🦄，','小马,','小🦄,','-mycoins','-mytrans','决斗','接受决斗','ttzf','izf','-myact']):
                y = time_meswithbot.get(t,0)
                y += 1
                time_meswithbot[t] = y
            # pattern= re.compile(r'^\[CQ\:image\,file.*subType\=1\,.*\]')
            if ('[CQ:image,file' in message and 'subType=1' in message):
                y = time_meswithimgemoji.get(t,0)
                y += 1
                time_meswithimgemoji[t] = y
        ct:datetime.datetime = deepcopy(st)
        while (ct<et):
            ct += datetime.timedelta(days=1)
            if ct>datetime.datetime.now():
                break
            t = ct.strftime('%Y-%m-%d')
            y = time_mes.get(t,0)
            if y==0:
                time_mes[t] = 0
            y = time_meswithbot.get(t,0)
            if y==0:
                time_meswithbot[t] = 0
            y = time_meswithimgemoji.get(t,0)
            if y==0:
                time_meswithimgemoji[t] = 0
        # sorted(time_mes.keys())
        x_list = list(time_mes.keys())
        y_list = list(time_mes.values())
        x_list = [datetime.datetime.strptime(x,'%Y-%m-%d') for x in x_list]
        # 消息最多的天
        y_max = max(y_list)
        x_max = x_list[y_list.index(y_max)].strftime('%Y 年 %m 月 %d 日')
        # 平均消息
        y_avg = messageNumber / (int((et.date()-st.date()).days)+1)
        if (y_max <= 5):
            messageDescript = '你是本群的潜水员，日最多发送信息少于 5 条'
            messageMedal.append('🎖️ 资深潜水')
        else:
            if y_avg<15:
                messageDescript = '你在本群低调内敛，平均每日发送信息 %.2f 条'%(y_avg)
            elif y_avg<50:
                messageDescript = '你在本群比较活跃，平均每日发送信息 %.2f 条'%(y_avg)
            else:
                messageDescript = '你在本群侃侃而谈，平均每日发送信息 %.2f 条'%(y_avg)
                messageMedal.append('🎖️ 水群大师')
            messageDescript += '\n%s，你一共发送了 %d 条信息'%(x_max, y_max)
        if messageNumber >=3000:
            messageMedal.append('🎖️ 活跃元老')
        elif y_max >=300:
            messageMedal.append('🎖️ 谈天说地')

        plt.figure(figsize=(10, 3)) 
        plt.bar(x_list, y_list, color='#87CEEB')
        ax = plt.gca()
        ax.set_facecolor('#E8F8FF')
        plt.xticks(rotation=25,size=9)
        time_dis_path = BytesIO()
        plt.margins(0.002, 0.1)
        plt.subplots_adjust(top=1,bottom=0,left=0,right=1,hspace=0,wspace=0) 
        plt.savefig(time_dis_path, dpi=200, bbox_inches='tight')
        card_content1 = [
            ('subtitle','共发送信息 %d 条\n'%(messageNumber),PALETTE_SJTU_BLUE),
            ('separator',),
            ('illustration', time_dis_path),
            ('body', messageDescript)
        ]
        if len(messageMedal) > 0:
            card_content1.append(('subtitle', '  '.join(messageMedal), PALETTE_SJTU_BLUE))

        # Bot互动-时间图
        x_list = list(time_meswithbot.keys())
        y_list = list(time_meswithbot.values())
        x_list = [datetime.datetime.strptime(x,'%Y-%m-%d') for x in x_list]
        messageWithBotNumber = sum(y_list)

        # Bot互动-奖章
        if (messageWithBotNumber>=500):
            messageWithBotMedal.append('🎖️ 高级测试工程师')
        elif (messageWithBotNumber>=200):
            messageWithBotMedal.append('🎖️ 中级测试工程师')
        elif (messageWithBotNumber>=50):
            messageWithBotMedal.append('🎖️ 初级测试工程师')
        if (messageWithBotNumber / messageNumber > 0.4):
            messageWithBotMedal.append('🎖️ 信息熵操纵者')
        plt.figure(figsize=(10, 3)) 
        plt.bar(x_list, y_list, color='#F8AC51')
        ax = plt.gca()
        ax.set_facecolor('#FFEFDD')
        plt.xticks(rotation=25,size=9)
        time_dis2_path = BytesIO()
        plt.margins(0.002, 0.1)
        plt.subplots_adjust(top=1,bottom=0,left=0,right=1,hspace=0,wspace=0) 
        plt.savefig(time_dis2_path, dpi=200, bbox_inches='tight')
        card_content2 = [
            ('subtitle','与小🦄共互动 %d 次\n'%(messageWithBotNumber),PALETTE_SJTU_ORANGE),
            ('separator',),
            ('illustration', time_dis2_path)
        ]
        if len(messageWithBotMedal) > 0:
            card_content2.append(('subtitle', '  '.join(messageWithBotMedal), PALETTE_SJTU_ORANGE))
        
        # 图片信息-时间图
        x_list = list(time_meswithimgemoji.keys())
        y_list = list(time_meswithimgemoji.values())
        x_list = [datetime.datetime.strptime(x,'%Y-%m-%d') for x in x_list]
        messageImgEmojiNumber = sum(y_list)
        if (messageImgEmojiNumber>=500):
            messageImgEmjMedal.append('🎖️ 表情包之神')
        plt.figure(figsize=(10, 3)) 
        plt.bar(x_list, y_list, color='#7DC473')
        ax = plt.gca()
        ax.set_facecolor('#E5FBE2')
        plt.xticks(rotation=25,size=9)
        time_dis3_path = BytesIO()
        plt.margins(0.002, 0.1)
        plt.subplots_adjust(top=1,bottom=0,left=0,right=1,hspace=0,wspace=0) 
        plt.savefig(time_dis3_path, dpi=200, bbox_inches='tight')
        plt.close()
        card_content3 = [
            ('subtitle','共发送动画表情 %d 次\n'%(messageImgEmojiNumber),PALETTE_SJTU_GREEN),
            ('separator',),
            ('illustration', time_dis3_path)
        ]
        if len(messageImgEmjMedal) > 0:
            card_content3.append(('subtitle', '  '.join(messageImgEmjMedal), PALETTE_SJTU_GREEN))
        
        img_avatar = Image.open(BytesIO(get_avatar_pic(user_id)))
        # 生成卡片图
        ActCards = ResponseImage(
            titleColor = PALETTE_SJTU_BLUE,
            title = '我的水群报告',
            layout = 'normal',
            width = 880,
            cardBodyFont= ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 24),
            cardSubtitleFont= ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 30),
        )
        ActCards.addCardList([
            ResponseImage.RichContentCard(
                raw_content=[
                    ('subtitle','ID : %d'%(user_id)),
                    ('separator',),
                    ('keyword','群 : %d'%(group_id))
                ],
                icon = img_avatar
            ),
            ResponseImage.RichContentCard(
                raw_content = card_content1
            ),
            ResponseImage.RichContentCard(
                raw_content = card_content2
            ),
            ResponseImage.RichContentCard(
                raw_content = card_content3
            )
        ])
        save_path = (os.path.join(SAVE_TMP_PATH, f'{user_id}_{group_id}_actReport.png'))
        ActCards.generateImage(save_path)
        return save_path
    except mysql.connector.Error as e:
        warning("mysql error in getMyActivity: {}".format(e))
    except BaseException as e:
        warning("error in getMyActivity: {}".format(e))
        
