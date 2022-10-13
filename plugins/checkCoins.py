from datetime import datetime
from typing import Union, Any
from utils.basicEvent import *
from utils.basicConfigs import *
from utils.standardPlugin import StandardPlugin
from utils.accountOperation import get_user_coins, get_user_transactions, update_user_coins
from PIL import Image, ImageDraw, ImageFont

class CheckCoins(StandardPlugin): # 查询当前金币
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg == '-mycoins'
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        text = f'[CQ:reply,id='+str(data['message_id'])+']您当前拥有金币：'+str(get_user_coins(data['user_id']))
        send(target, text, data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'CheckCoins',
            'description': '查询当前金币',
            'commandDescription': '-mycoins',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
class AddAssignedCoins(StandardPlugin): # 测试时使用，给指定用户增加金币
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return (msg.startswith('-addcoins ') and data['user_id'] in ROOT_ADMIN_ID)
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        msg=msg.replace('-addcoins ','',1)
        msg_split=msg.strip().split()
        try:
            num_id=int(msg_split[0])
            num_append=float(msg_split[1])
        except:
            return "OK"
        update_user_coins(num_id, num_append, '管理员-addcoins命令')
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'AddAssignedCoins',
            'description': '给指定用户增加金币,仅管理员可用',
            'commandDescription': '-addcoins [user_id]',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
class CheckTransactions(StandardPlugin): # 查询近期交易记录
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg == '-mytrans'
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        #print(data['user_id'])
        ret = draw_trans_cards(data['user_id'])
        pic_path=(f'file:///{ROOT_PATH}/'+ret)
        send(target, '[CQ:reply,id='+str(data['message_id'])+f'][CQ:image,file={pic_path}]',data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'CheckTransactions',
            'description': '查询近期交易记录',
            'commandDescription': '-mytrans',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
def draw_trans_cards(id):
    trans_list = get_user_transactions(id)
    qqid=id
    height=270+110*len(trans_list)
    width=720
    img = Image.new('RGBA', (width, height), (244, 149 ,4, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 120, width, height), fill=(255, 255, 255, 255))
    draw.text((width-300,40), "交易记录", fill=(255,255,255,255), font=font_hywh_85w)
    draw.text((width-120,44), "LITTLE\nUNIkeEN", fill=(255,255,255,255), font=font_syht_m)
    i=1
    for id, timestp, qq, change, balance, description in trans_list:
        draw.text((90, 70+110*i),description,fill=(0,0,0,255), font=font_hywh_85w_ms)
        draw.text((90, 70+110*i+50),str(timestp),fill=(175,175,175,255), font=font_hywh_85w_s)
        txt_size = draw.textsize(str(change/100), font=font_hywh_85w_ms)
        draw.text((width-txt_size[0]-90, 70+110*i),str(change/100),fill=(FONT_CLR['r'] if change>0 else FONT_CLR['g']), font=font_hywh_85w_ms)
        txt_size = draw.textsize(f"余额：{str(balance/100)}", font=font_hywh_85w_s)
        draw.text((width-txt_size[0]-90, 70+110*i+50),f"余额：{str(balance/100)}",fill=(175,175,175,255), font=font_hywh_85w_s)
        i+=1
    draw.text((30,height-48),'仅显示最近20条交易记录', fill=(175,175,175,255), font=font_syht_m)
    if len(trans_list)==0:
        txt_size = draw.textsize("暂无交易记录", font=font_hywh_85w_ms)
        draw.text((90, 150),"暂无交易记录",fill=(175,175,175,255), font=font_hywh_85w_s)
    save_path=(f'{SAVE_TMP_PATH}/{qqid}_trans.png')
    img.save(save_path)
    return (save_path)

        

