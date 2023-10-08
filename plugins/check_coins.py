from typing import Union, Any
from utils.basic_event import *
from utils.basic_configs import *
from utils.standard_plugin import StandardPlugin
from utils.account_operation import get_user_coins, get_user_transactions, update_user_coins
from PIL import Image, ImageDraw, ImageFont
import os.path, re

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
    def __init__(self) -> None:
        self.pattern = re.compile(r'^\-addcoins\s+(\d+|\[CQ\:at\,qq=\d+\])\s+(\-?\d+(\.\d+)?)$')
        self.cqAtPattern = re.compile(r'\[CQ\:at\,qq=(\d+)\]')
        self.numPattern = re.compile(r'^\d+$')
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return self.pattern.match(msg) != None and data['user_id'] in ROOT_ADMIN_ID
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        num_id, num_append, _ = self.pattern.findall(msg)[0]
        num_append = float(num_append)
        if self.numPattern.match(num_id) != None:
            num_id = int(num_id)
        elif self.cqAtPattern.match(num_id) != None:
            num_id = int(self.cqAtPattern.findall(num_id)[0])
            print(num_id)
        else:
            send(target, '[CQ:reply,id=%d]命令解析失败'%data['message_id'], data['message_type'])
            return "OK"
        update_user_coins(num_id, num_append, '管理员-addcoins命令')
        send(target, '[CQ:reply,id=%d]OK'%data['message_id'], data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'AddAssignedCoins',
            'description': '给指定用户增加金币[🔒]',
            'commandDescription': '-addcoins @{..} <money>',
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
        picPath = draw_trans_cards(data['user_id'])
        picPath = picPath if os.path.isabs(picPath) else os.path.join(ROOT_PATH, picPath)
        send(target, '[CQ:reply,id=%d][CQ:image,file=files:///%s]'%(data['message_id'], picPath),data['message_type'])
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
def draw_trans_cards(id: int):
    id = id if isinstance(id, int) else int(id)
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
    save_path=os.path.join(SAVE_TMP_PATH, f'{qqid}_trans.png')
    img.save(save_path)
    return (save_path)

        

