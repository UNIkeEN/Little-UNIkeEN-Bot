import json
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from utils.basicConfigs import BACK_CLR,FONT_CLR

FONTS_PATH = 'resources/fonts'
SAVE_TMP_PATH = 'data/tmp'
font_syht_m = ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Normal.otf'), 18)
font_hywh_85w_ms = ImageFont.truetype(os.path.join(FONTS_PATH, '汉仪文黑.ttf'), 26)
font_hywh_85w = ImageFont.truetype(os.path.join(FONTS_PATH, '汉仪文黑.ttf'), 40)
font_sg_emj = ImageFont.truetype(os.path.join(FONTS_PATH, 'seguiemj.ttf'), 40)

# 默认功能列表
DEFAULT_CONFIG={
    "Faq":{
        "name":"问答库",
        "command":"问 [title]",
        "enable":False
    },
    "Auto_Answer":{
        "name":"智能对话",
        "command":"小马/小🦄，[msg]",
        "enable":True,
        "mode":"answerbook" # answerbook/nlp
    },
    "Greetings":{
        "name":"早安晚安",
        "command":"早安/晚安",
        "enable":True
    },
    "SuperEmoji":{
        "name":"超级表情",
        "command":"投篮/烟花/鞭炮",
        "enable":True
    },
    "DailyNews":{
        "name":"新闻聚合",
        "command":"新闻/每日新闻",
        "enable":True
    },
    "2cyPIC":{
        "name":"二次元图",
        "command":"来点图图",
        "enable":True
    },
    "Sign_in":{
        "name":"每日签到",
        "command":"签到/每日签到/打卡",
        "enable":True
    },
    "Roulette":{
        "name":"俄罗斯轮盘",
        "command":"装弹/轮盘 [params]",
        "enable":True
    },
    "Lottery":{
        "name":"三色彩",
        "command":"彩票帮助/买彩票 [params]",
        "enable":True
    },
    "Sjtu_Info":{
        "name":"校园服务",
        "command":"-lib/-st/-sjmc/-dekt",
        "enable":True
    },
    "Ys_Note":{
        "name":"原神便笺",
        "command":"-ys note",
        "enable":False
    },
    "MaintainConfig":{
        "name":"维护权限",
        "command":"-group cfg [cmd]",
        "enable":True
    },
    "Insider":{
        "name":"内测功能",
        "command":"更多功能请自行探索~",
        "enable":False
    },
    "Admin":{
        "name":"本群管理员",
        "list":[2641712741]
    }
}
# 私聊功能列表（展示）
PRI_FUNC_DICT={
    "DailyNews":{
        "name":"新闻聚合",
        "command":"新闻/每日新闻",
        "enable":True
    },
    "sePIC":{
        "name":"图图Plus",
        "command":"来点涩涩 [tags(可选,可多个)]",
        "enable":False
    },
    "Sign_in":{
        "name":"每日签到",
        "command":"签到/每日签到/打卡",
        "enable":True
    },
    "Lottery":{
        "name":"三色彩",
        "command":"彩票帮助/买彩票 [params]",
        "enable":True
    },
    "Stocks":{
        "name":"股市查询",
        "command":"查股票/查股价(帮助)",
        "enable":True
    },
    "Sjtu_Info":{
        "name":"校园服务",
        "command":"-lib/-st/-sjmc/-dekt",
        "enable":True
    },
    "Canvas_Sync":{
        "name":"日历馈送",
        "command":"-ddl/-canvas",
        "enable":True
    },
    "Ys_Note":{
        "name":"原神便笺",
        "command":"-ys note",
        "enable":True
    },
    "Check_Coins":{
        "name":"我的钱包",
        "command":"-mycoins/-mytrans(记录)",
        "enable":True
    },
}

def check_config(group_id, cmd_name, admin=False, qq_id=0): #admin则检测是否需要鉴管理员权限
    data_path=(f'data/{group_id}/config.json')
    if not Path(data_path).is_file():
        with open(data_path, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
    with open(data_path, "r") as f2:
        config = json.load(f2)
    if admin:
        return (qq_id in config["Admin"]["list"])
    return config[cmd_name]['enable']

def check_config_mode(group_id, cmd_name): # 如有mode返回mode
    data_path=(f'data/{group_id}/config.json')
    if not Path(data_path).is_file():
        with open(data_path, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
    with open(data_path, "r") as f2:
        config = json.load(f2)
    if not config[cmd_name]['enable']:
        return None
    try:
        ret = config[cmd_name]['mode']
        return ret
    except:
        return None

def edit_config(group_id, cmd_name, enable):
    data_path=(f'data/{group_id}/config.json')
    if not Path(data_path).is_file():
        with open(data_path, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
    with open(data_path, "r") as f2:
        config = json.load(f2)
    try:
        config[cmd_name]["enable"]=enable
        with open(data_path, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except:
        return False

def add_admin(group_id, new_id):
    data_path=(f'data/{group_id}/config.json')
    if not Path(data_path).is_file():
        with open(data_path, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
    with open(data_path, "r") as f2:
        config = json.load(f2)
    try:
        if new_id not in config['Admin']['list']:
            config['Admin']['list'].append(int(new_id))
        with open(data_path, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except:
        return False
    
def show_config_card(group_id):
    i=1
    if group_id !=0:
        data_path=(f'data/{group_id}/config.json')
        if not Path(data_path).is_file():
            with open(data_path, 'w') as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)
        with open(data_path, "r") as f2:
            config_base = json.load(f2)
        height=450+80*len(config_base)+80*(len(config_base['Admin']['list'])-1)+80*(len(PRI_FUNC_DICT))
        width=980
        img = Image.new('RGBA', (width, height), (6,162,183,255))
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, 120, width, height), fill=(255, 255, 255, 255))
        draw.text((120, 150), f"群号:{group_id}", fill=(6,162,183,255), font=font_hywh_85w)
        draw.text((60, 230), "●", fill=(6,162,183,255), font=font_hywh_85w)
        draw.text((120, 230), f"群聊功能", fill=(6,162,183,255), font=font_hywh_85w)
        i+=2
        for cf_value in config_base.values():
            if cf_value['name']=="本群管理员":
                draw.text((120, 70+i*80), cf_value['name'] ,fill=(0, 0, 0, 255), font=font_hywh_85w)
                for j in range(len(cf_value['list'])):
                    draw.text((360, 70+(i+j)*80), f"{cf_value['list'][j-1]}", fill=(0, 0, 0, 255), font=font_hywh_85w)
                i+=len(cf_value['list'])
            elif cf_value['name']=="智能对话":
                clr = (0,0,0,255) if cf_value['enable'] else (185,185,185,255)
                draw.text((120, 70+i*80), cf_value['name'] ,fill=clr, font=font_hywh_85w)
                draw.text((360, 70+i*80), f"'{cf_value['command'][:4]}", fill=clr, font=font_hywh_85w)
                txt_size = draw.textsize(f"'{cf_value['command'][:4]}", font=font_hywh_85w)[0]
                draw.text((360+txt_size, 70+i*80), "🦄", fill=clr, font=font_sg_emj)
                txt_size = txt_size+ draw.textsize("🦄", font=font_sg_emj)[0]
                draw.text((360+txt_size, 70+i*80), f"{cf_value['command'][5:]}'", fill=clr, font=font_hywh_85w)
                txt_size = txt_size+ draw.textsize(f"{cf_value['command'][5:]}'", font=font_hywh_85w)[0]
                if cf_value['enable']:
                    draw.text((60, 70+i*80), "√", fill=(0, 0, 0, 255), font=font_hywh_85w)
                    mode = "答案之书" if cf_value['mode']=="answerbook" else "NLP"
                    clr_index = 'g' if mode=='答案之书' else 'o' 
                    txt_size2 = draw.textsize(mode+"模式", font=font_hywh_85w_ms)[0]
                    draw.rectangle((360+txt_size+20, 70+i*80, 360+txt_size+txt_size2+40, 70+i*80+50), fill=BACK_CLR[clr_index])
                    draw.text((360+txt_size+30, 70+i*80+10), mode+"模式", fill=FONT_CLR[clr_index], font=font_hywh_85w_ms)
                i+=1
            else:
                try:
                    if cf_value['enable']:
                        draw.text((120, 70+i*80), cf_value['name'] ,fill=(0, 0, 0, 255), font=font_hywh_85w)
                        draw.text((360, 70+i*80), f"'{cf_value['command']}'", fill=(0, 0, 0, 255), font=font_hywh_85w)
                        draw.text((60, 70+i*80), "√", fill=(0, 0, 0, 255), font=font_hywh_85w)
                    else:
                        draw.text((120, 70+i*80), cf_value['name'] ,fill=(185, 185, 185, 255), font=font_hywh_85w)
                        draw.text((360, 70+i*80), f"'{cf_value['command']}'", fill=(185, 185, 185, 255), font=font_hywh_85w)
                    i+=1
                except:
                    pass
    else:
        height=270+80*(len(PRI_FUNC_DICT))
        width=960
        img = Image.new('RGBA', (width, height), (6,162,183,255))
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, 120, width, height), fill=(255, 255, 255, 255))
    draw.text((width-300,40), "功能配置", fill=(255,255,255,255), font=font_hywh_85w)
    draw.text((width-120,44), "LITTLE\nUNIkeEN", fill=(255,255,255,255), font=font_syht_m)
    draw.text((60, 70+i*80), "●", fill=(6,162,183,255), font=font_hywh_85w)
    draw.text((120, 70+i*80), f"私聊功能", fill=(6,162,183,255), font=font_hywh_85w)
    i+=1
    for pri_func in PRI_FUNC_DICT.values():
        if pri_func['enable']:
            draw.text((120, 70+i*80), pri_func['name'] ,fill=(0, 0, 0, 255), font=font_hywh_85w)
            draw.text((360, 70+i*80), f"'{pri_func['command']}'", fill=(0, 0, 0, 255), font=font_hywh_85w)
        else:
            draw.text((120, 70+i*80), pri_func['name'] ,fill=(185, 185, 185, 255), font=font_hywh_85w)
            draw.text((360, 70+i*80), f"'{pri_func['command']}'", fill=(185, 185, 185, 255), font=font_hywh_85w)    
        i+=1
    save_path=(f'{SAVE_TMP_PATH}/{group_id}_config.png')
    img.save(save_path)
    return save_path
    