from PIL import Image, ImageDraw, ImageFont
import random
from threading import Timer
from io import BytesIO
from typing import Union, Any
from utils.basicEvent import *
from utils.basicConfigs import *
from utils.standardPlugin import StandardPlugin
from utils.accountOperation import get_user_coins, update_user_coins
import re

# 轮盘赌类，每个群创建一个实例
class _roulette():
    def __init__(self, group_id):
        self.player=[]
        self.status='init'
        self.wager=0
        self.aim_id=None # 决斗发起方的aim_id
        self.can_settle=False # 是否可以超时结算
        self.group_id=group_id # 群号（用于读取金币数量）
        self.round_index=0 # 在0和1之间切换，对应当前开枪者
        # status:
        #'init'--等待开始决斗,'prepare'--准备阶段',ongoing'--正在决斗（无法强制结束）
        self.bullet_index=[]
        self.num_whole=0
        #self.random_bullet(num_bullet, num_whole)
        self.cur_index=0
        self.timer=Timer

    def get_cmd(self, id, msg):
        # init阶段，发起决斗申请
        initPattern = re.compile(r'^(装弹|轮盘|决斗)\s+(\d+)\s+(\d+)\s+(\d+)\s*(\[CQ:at,qq=\d+\])?$')
        if initPattern.match(msg) != None:
            if self.status!='init':
                ret_p=''
                if self.status=='prepare':
                    ret_p=(f'\n\n当前决斗请求：\n发起者：{self.player[0]}\n特定邀请对象：{self.aim_id}\n挑战金额：{self.wager}\n子弹数：{len(self.bullet_index)} in {self.num_whole}')
                if self.status=='ongoing':
                    ret_p=(f'\n\n当前正在进行决斗：\n{self.player[0]} vs {self.player[1]}\n挑战金额：{self.wager}\n子弹数：{len(self.bullet_index)} in {self.num_whole}')
                return ERR_DESCRIBES[4]+ret_p
            else:
                _, num_bul, num_who, num_wager, aim_id = initPattern.findall(msg)[0]
                num_bul = int(num_bul)
                num_who = int(num_who)
                num_wager = int(num_wager)
                if num_who<3 or num_who>30: #轮盘总格数在[3,30]之间
                    return ERR_DESCRIBES[1]
                if num_bul>=num_who or num_bul<1:   #装入子弹数必须小于轮盘总格数
                    return ERR_DESCRIBES[2]
                if num_wager<10:
                    return ERR_DESCRIBES[13]
                tmp = get_user_coins(id)
                if num_wager>tmp: # 赌注必须小于已有金币
                    return ERR_DESCRIBES[5].format(coins=tmp)
                self.__init__(self.group_id)
                self.wager=num_wager
                self.player.append(id)
                # print(self.player)
                qqExtractor = re.compile(r'^\[CQ:at,qq=(\d+)\]$')
                if qqExtractor.match(aim_id) != None:
                    aim_id = int(qqExtractor.findall(aim_id)[0])
                    if aim_id==self.player[0]:
                        return ERR_DESCRIBES[3]
                    if aim_id==BOT_SELF_QQ:
                        return ERR_DESCRIBES[6]
                    self.aim_id = aim_id
                    tmp = get_user_coins(self.aim_id)
                    if self.wager>tmp: # 检查决斗对象赌注金额
                        self.__init__(self.group_id)
                        return ERR_DESCRIBES[11].format(aim_id=str(self.aim_id))
                self.random_bullet(num_bul, num_who) # 随机填入子弹
                self.num_whole=num_who
                self.status='prepare'
                self.timer=Timer(45, self.prepare_timeout)
                self.timer.start()
                if self.aim_id==None:
                    return (f'🚩{self.player[0]}向群友发起决斗请求！\n\n - 挑战金额：{self.wager} 子弹数：{len(self.bullet_index)} in {self.num_whole}\n - 愿意接受的勇敢者请回复【接受决斗】，支付相同金币并参加决斗\n - 未应答前，发起者可以发送【取消决斗】取消，45s无应答自动取消🚩')
                else:
                    return (f'🚩{self.player[0]}向{self.aim_id}发起决斗请求！\n\n - 挑战金额：{self.wager} 子弹数：{len(self.bullet_index)} in {self.num_whole}\n - 若[CQ:at,qq={self.aim_id}]愿意，请回复【接受决斗】，支付相同金币参加决斗\n - 若不愿意，请回复【拒绝决斗】\n - 未应答前，发起者可以发送【取消决斗】取消，45s无应答自动取消🚩')   
        # prepare阶段，接受决斗申请
        elif msg in ['接受', '接受决斗']:
            if id==self.player[0]:
                return ERR_DESCRIBES[10][:5]
            if self.status!='prepare':
                return ERR_DESCRIBES[7]
            else:
                if self.aim_id!=None: # 面向特定群友
                    if id!=self.aim_id:
                        return ERR_DESCRIBES[10]
                else: # 面向所有群友
                    if id==self.player[0]:
                        return ERR_DESCRIBES[8]
                    tmp = get_user_coins(id) # 检查接受者金币数量
                    if self.wager>tmp: 
                        return ERR_DESCRIBES[9].format(coins=tmp)
                update_user_coins(id, -self.wager, '轮盘开始-扣除挑战金额')
                update_user_coins(self.player[0], -self.wager, '轮盘开始-扣除挑战金额')
                self.player.append(id)
                self.begin_game()
                self.round_index=0
                return (f"{self.player[0]}和{self.player[1]}的决斗拉开帷幕！\n------\n发送“咔/嘭/嘣/砰/开枪 [开枪次数(可选，默认为1)]”以开枪\n")+(f'请发起方[CQ:at,qq={self.player[self.round_index]}]在30s内开枪，超时自动判负')
        # prepare阶段，拒绝决斗申请
        elif msg in ['拒绝', '拒绝决斗']:
            if self.status!='prepare':
                return ERR_DESCRIBES[7]
            if self.aim_id==id:
                ret = (f"{id}拒绝了{self.player[0]}发起的决斗！")
                self.timer.cancel()
                self.__init__(self.group_id)
                return ret
        elif msg in ['取消', '取消决斗'] and self.status=='prepare':
            if id==self.player[0]:
                self.timer.cancel()
                self.__init__(self.group_id)
                return "取消决斗成功"
            else:
                return ERR_DESCRIBES[14]
        # ongoing阶段，决斗
        elif startswith_in(msg, CMD_ROULETTE_ONGOING) and self.status=='ongoing':
            if id==self.player[1-self.round_index]:
                return ERR_DESCRIBES[12]
            if id not in self.player:
                return ERR_DESCRIBES[10][:5]
            msg_split=msg.split()
            num_shot=0
            try:
                num_shot=int(msg_split[1])
            except:
                num_shot=1
            if num_shot<=0:
                return ERR_DESCRIBES[10][:2]+'调皮'+ERR_DESCRIBES[10][4]
            return(self.shot(num_shot))

    def prepare_timeout(self): # 准备阶段超时无人应答
        self.timer.cancel()
        send(self.group_id,f'⏰45s内无应答，{self.player[0]}的决斗请求已自动取消')
        self.__init__(self.group_id)
        return

    def ongoing_timeout(self): # 游戏阶段超时无人应答
        self.timer.cancel()
        send(self.group_id,f'⏰30s内无应答，决斗已自动结算，胜利者为{self.player[1-self.round_index]}')
        update_user_coins(self.player[1-self.round_index], 2*self.wager, '轮盘获胜奖励')
        ret = self.result(self.player[1-self.round_index],self.player[self.round_index])
        #self.__init__(self.group_id) 在result中执行了
        r_path=os.path.dirname(__file__)
        pic_path=(f'file:///{r_path}/'[:-8]+ret)
        if ret!=None:
            send(self.group_id, f'[CQ:image,file={pic_path}]')
        return

    def shot(self, num_shot): # 开枪
        self.timer.cancel()    
        for i in range(num_shot):
            self.cur_index+=1
            if self.cur_index in self.bullet_index:
                ret = (f'[CQ:at,qq={self.player[self.round_index]}]:\n')
                ret += random.choice(DEAD_TEXT)+(f'\n------\n游戏结束！\n已进行到第{self.cur_index}发，轮盘共{self.num_whole}格，填入子弹{len(self.bullet_index)}颗')
                update_user_coins(self.player[1-self.round_index], 2*self.wager, '轮盘获胜奖励')
                send(self.group_id, ret)
                return self.result(self.player[1-self.round_index],self.player[self.round_index])
        self.round_index=1-self.round_index # 切换下一个开枪者
        tmp = random.choice(ALIVE_TEXT)+(f'\n------\n已进行到第{self.cur_index}发，轮盘共{self.num_whole}格，填入子弹{len(self.bullet_index)}颗')
        self.timer=Timer(30,self.ongoing_timeout)
        self.timer.start()
        return (f'[CQ:at,qq={self.player[1-self.round_index]}]:\n')+tmp+(f'\n请[CQ:at,qq={self.player[self.round_index]}]在30s内开枪，超时自动判负')

    def random_bullet(self, num_bullet, num_whole): # 随机生成子弹
        self.bullet_index=[]
        for i in range(num_bullet):
            while True:
                ran = random.randint(1,num_whole)
                if ran not in self.bullet_index:
                    self.bullet_index.append(ran)
                    break

    def begin_game(self): # 开始比赛
        self.status='ongoing'  
        self.timer.cancel()    
        self.timer=Timer(30,self.ongoing_timeout)  
        self.timer.start()

    def result(self,win_qqid,loser_qqid):
        self.timer.cancel()
        height=820
        width=720
        wager = self.wager
        self.__init__(self.group_id)
        try:
            img = Image.new('RGBA', (width, height), (244, 149 ,4, 255))
            draw = ImageDraw.Draw(img)
            draw.rectangle((0, 120, width, height), fill=(255, 255, 255, 255))
            draw.text((width-340,40), "俄罗斯轮盘", fill=(255,255,255,255), font=font_hywh_85w)
            draw.text((width-120,44), "LITTLE\nUNIkeEN", fill=(255,255,255,255), font=font_syht_m)
            txt_size = draw.textsize('⚔️', font=font_sg_emj_l)
            draw.text(((width-txt_size[0])/2,180), "⚔️", fill=(120,120,120,255), font=font_sg_emj_l)
            txt_size = draw.textsize('俄罗斯轮盘 - 对决结果', font=font_hywh_85w)
            draw.text(((width-txt_size[0])/2,290), "俄罗斯轮盘 - 对决结果", fill=(0,0,0,255), font=font_hywh_85w)
            # 圆形蒙版
            mask = Image.new('RGBA', (100, 100), color=(0,0,0,0))
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0,0, 100, 100), fill=(159,159,160))
            # 获取头像1
            avatar1 = get_avatar_pic(win_qqid)
            if avatar1 != None:
                img_avatar1 = Image.open(BytesIO(avatar1))
                img.paste(img_avatar1, (60, 420), mask)

            # 获取头像2
            avatar2 = get_avatar_pic(loser_qqid)
            if avatar2 != None:
                img_avatar2 = Image.open(BytesIO(avatar2))
                img.paste(img_avatar2, (60, 570), mask)

            draw.text((210,420),f'胜利者：{win_qqid}', fill=(221, 0, 38, 255),font=font_hywh_85w)
            draw.text((210,490),f'金币+{wager} -> 当前金币：{get_user_coins(win_qqid)}', fill=(175, 175, 175, 255),font=font_hywh_85w_mms)
            draw.text((210,570),f'失败者：{loser_qqid}', fill=(0, 191, 48, 255),font=font_hywh_85w)
            draw.text((210,640),f'金币-{wager} -> 当前金币：{get_user_coins(loser_qqid)}', fill=(175, 175, 175, 255),font=font_hywh_85w_mms)
            draw.text((60,720),'发起新的决斗：\n装弹/轮盘/决斗 [子弹数] [轮盘总格数] [挑战金额] [@决斗对象(可选)]\n举例：装弹 2 7 100 @xxx',fill=(175, 175, 175, 255), font=font_syht_m)
            save_path=(f'{SAVE_TMP_PATH}/{self.group_id}_roulette.png')
            img.save(save_path)
            return save_path
        except:
            return None
        

# 插件类，响应bot事件
class RoulettePlugin(StandardPlugin):
    def __init__(self) -> None:
        self.roulette_dict={}
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        if data['message_type']!='group': return False
        group_id = data['group_id']
        if group_id not in self.roulette_dict.keys():
            self.roulette_dict[group_id] = _roulette(group_id)
        return startswith_in(msg, CMD_ROULETTE) or \
            (startswith_in(msg, CMD_ROULETTE_ONGOING) and \
            self.roulette_dict[group_id].status=='ongoing')
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        group_id = data['group_id']
        ret = self.roulette_dict[group_id].get_cmd(data['user_id'],msg)
        if ret == None: return
        try:
            if ret[-3:]=='png':
                picPath = ret if os.path.isabs(ret) else os.path.join(ROOT_PATH, ret)
                send(group_id, f'[CQ:image,file=files:///{picPath}]')
            else:
                send(group_id, ret)
        except BaseException as e:
            warning("base exception in RoulettePlugin.executeEvent: {}".format(e))
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'RoulettePlugin',
            'description': '轮盘赌',
            'commandDescription': '装弹/轮盘/决斗',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
# 以下为轮盘赌实类 
CMD_ROULETTE=['装弹','轮盘','决斗','接受决斗','接受','拒绝决斗','拒绝','结算','取消决斗','取消']
CMD_ROULETTE_ONGOING=['咔','嘭','嘣','砰','开枪']
ERR_DESCRIBES=[
    '发起决斗失败\n参数错误。发起决斗命令格式：\n装弹/轮盘/决斗 [子弹数] [轮盘总格数] [挑战金额(需为整数)] [@决斗对象(可选)]\n举例：装弹 2 7 100 @xxx', # 0
    '发起决斗失败\n参数错误：轮盘总格数需要在[3,30]之间', # 1
    '发起决斗失败\n参数错误：装入子弹数必须大于0且小于轮盘总格数', # 2
    '发起决斗失败\n不能和自己决斗！', # 3
    '发起决斗失败\n本群有正在进行的决斗（请求）', # 4
    '发起决斗失败\n您的金币不足。您目前有【{coins}】枚金币，设定的挑战金额不得大于此数目！', # 5
    '发起决斗失败\n不能和Bot决斗！', # 6
    '接受/拒绝决斗失败\n本群暂无未响应的决斗申请', # 7
    '接受/拒绝决斗失败\n不能和自己决斗！', # 8
    '接受/拒绝决斗失败\n您的金币不足。您目前有【{coins}】枚金币，小于发起者所制定的挑战金额！', # 9
    '不要捣乱😎，发起人找的不是你哦！', # 10
    '发起决斗失败\n指定决斗对象{aim_id}的金币不足支付挑战金额！', # 11
    '还没轮到你开枪哦~', # 12
    '发起决斗失败\n参数错误：挑战金额必须是大于10的正数', # 13
    '取消决斗失败\n你不是请求发起人' # 14
]
DEAD_TEXT=[
    '"嘭！"，你直接去世了',
    '"这里是天堂，还是地狱？"',
    '终究还是你先走一步...',
    '寄汤来咯！你终究还是没能逃脱命运的枷锁',
    '无情的子弹穿透了你的小脑壳',
    '你感受到了子弹的动能',
    '生命...终有尽时...',
    '让世界...彻底遗忘我',
    '败者...没有借口...',
    '浮世景色百千年依旧，人之在世却如白露与泡影，虚无。——雷电将军',
    '可惜，枫叶红时，总多离别。——枫原万叶'
]
ALIVE_TEXT=[
    '呼呼，没有爆裂的声响，你活了下来',
    '虽然黑洞洞的枪口很恐怖，但好在没有子弹射出来',
    '你睁开了双眼，世界仍然是一片静好。',
    '无事发生，你活下来了',
    '命运的女神给予你眷顾，你活下来了',
    '轮盘依旧旋转，你的时间没有停止流淌',
]

