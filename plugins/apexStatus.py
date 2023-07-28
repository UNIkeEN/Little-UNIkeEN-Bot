from utils.standardPlugin import StandardPlugin, Any, Union
import requests
from utils.basicEvent import *
from utils.basicConfigs import *
from pathlib import Path
from utils.responseImage_beta import ResponseImage
from resources.api.apexAPI import APEX_AUTHKEY
import json

APEX_MAIN_COLOR="#E54722"

MAP_NAME = {"Olympus":"奥林匹斯", 
            "Kings Canyon":"诸王峡谷", 
            "Storm Point":"风暴点",
            "World's Edge":"世界尽头",
            "Broken Moon":"残月",
            "Habitat":"栖息地",
            "Skulltown":"骷髅镇",
            "Hammond Labs":"哈蒙德实验室",
            "Phase Runner":"相位穿梭器",
            "Overflow":"熔岩流",
            "Party Crasher":"派对破坏者",
            "Siphon":"岩浆提取器",
            "Caustic Treatment":"侵蚀疗法",
            "Fragment":"碎片（原碎片东部）",
            "Estates":"不动产"
            }

MODE_NAME = {"TDM":"团队死斗",
            "Gun Run":"子弹时间",
            "Control":"控制",
            }

CRAFTING_TRANSLATION = {
            'optic_variable_sniper' : '4倍至8倍可调节式光学瞄准镜',
            'optic_variable_aog' : '2倍至4倍可调节式高级光学瞄准镜',
            'optic_hcog_ranger' : '3倍全息衍射式瞄准镜"游侠"',  
            'optic_hcog_bruiser' : '2倍全息衍射式瞄准镜"格斗家"',
            'optic_digital_threat' : '单倍数字化威胁',
            # 弹匣
            'extended_light_mag' : '加长式轻型弹匣 - 等级3',
            'extended_heavy_mag' : '加长式重型弹匣 - 等级3',
            'extended_energy_mag' : '加长式能量弹匣 - 等级3',
            'extended_sniper_mag' : '加长式狙击弹匣 - 等级3',
            # 其余枪械部件
            'barrel_stabilizer' : '枪管稳定器 - 等级3',
            'shotgun_bolt' : '霰弹枪栓 - 等级4',
            'standard_stock' : '标准枪托 - 等级3',
            'sniper_stock' : '狙击枪托 - 等级3',
            # 即用配件
            'boosted_loader' : '加速装填器',
            'turbocharger' : '涡轮增压器',
            "deadeye's_tempo" : '神射手速度节拍',
            'hammerpoint_rounds' : '锤击点',
            'kinetic_feeder' : '动能供弹器',
            'shatter_caps' : '粉碎帽',
            #每周
            'mobile_respawn_beacon' : '移动重生信标',
            'knockdown_shield' : '击倒护盾 - 等级3',
            'backpack' : '背包 - 等级3',
            'helmet' : '头盔 - 等级3'
        }

class ApexStatusPlugin(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return startswith_in(msg, ['-apex'])
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        try:
            imgPath = getApexStatusImg()
            if imgPath == None:
                send(data['group_id'], 'Apex API 请求失败', data['message_type'])
            else:
                imgPath = imgPath if os.path.isabs(imgPath) else os.path.join(ROOT_PATH, imgPath)
                send(target, '[CQ:image,file=files:///%s]'%imgPath, data['message_type'])
        except BaseException as e:
            send(data['group_id'], '内部错误：{}'.format(e), data['message_type'])
            warning("Exception in Apex: {}".format(e))
        
        return "OK"
    def getPluginInfo(self, )->dict:
        return {
            'name': 'ApexStatus',
            'description': 'APEX游戏状态',
            'commandDescription': '-apex',
            'usePlace': ['group',],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }

def transName(eng):
    tmp = MAP_NAME.get(eng)
    tmp = MODE_NAME.get(eng, tmp)
    tmp = CRAFTING_TRANSLATION.get(eng, tmp)
    return tmp if tmp!=None else eng

def HexToRgb(hex):
    hex = hex.lstrip('#')
    rgba = tuple(int(hex[i:i+2], 16) for i in (0, 2, 4))
    rgba += (255,)
    return rgba

def getApexStatusImg():
    # 地图轮换
    url = f"https://api.mozambiquehe.re/maprotation?version=2&auth={APEX_AUTHKEY}"
    ret = requests.get(url=url)
    ret = ret.json()
    # mapinfo = f"匹配：{transName(ret['battle_royale']['current']['map'])}（余{ret['battle_royale']['current']['remainingTimer']}）\n\t接下来：{transName(ret['battle_royale']['next']['map'])}"
    # mapinfo += f"\n排位赛：{transName(ret['ranked']['current']['map'])}（余{ret['ranked']['current']['remainingTimer']}）\n\t接下来：{transName(ret['ranked']['next']['map'])}"
    # mapinfo += f"\n街机模式：{transName(ret['ltm']['current']['eventName'])}-{transName(ret['ltm']['current']['map'])}（余{ret['ltm']['current']['remainingTimer']}）\n\t接下来：{transName(ret['ltm']['next']['eventName'])}-{transName(ret['ltm']['next']['map'])}"

    
    card_mapinfo = [
        ('title', '地图轮换', HexToRgb(APEX_MAIN_COLOR)),
        ('separator',),
    ]
    current_battle_royale_map_asset = ret['battle_royale']['current']['asset']
    if current_battle_royale_map_asset:
        card_mapinfo.append(('illustration', os.path.join(IMAGES_PATH, 'apex/' + current_battle_royale_map_asset.split('/')[-1])))
    card_mapinfo += [
        ('subtitle', '匹配：{}'.format(transName(ret['battle_royale']['current']['map']))),
        ('body', '剩余时间：{}   接下来：{}'.format(ret['battle_royale']['current']['remainingTimer'], transName(ret['battle_royale']['next']['map']))),
        ('separator',),
    ]
    current_ranked_map_asset = ret['ranked']['current']['asset']
    if current_ranked_map_asset:
        card_mapinfo.append(('illustration', os.path.join(IMAGES_PATH, 'apex/' + current_ranked_map_asset.split('/')[-1])))
    card_mapinfo += [
        ('subtitle', '排位赛：{}'.format(transName(ret['ranked']['current']['map']))),
        ('body', '剩余时间：{}   接下来：{}'.format(ret['ranked']['current']['remainingTimer'], transName(ret['ranked']['next']['map']))),
        ('separator',),
    ]
    current_ltm_map_asset = ret['ltm']['current']['asset']
    if current_ltm_map_asset:
        card_mapinfo.append(('illustration', os.path.join(IMAGES_PATH, 'apex/' + current_ltm_map_asset.split('/')[-1])))
    card_mapinfo += [
        ('subtitle', '街机模式：{} - {}'.format(transName(ret['ltm']['current']['eventName']), transName(ret['ltm']['current']['map']))),
        ('body', '剩余时间：{}   接下来：{} - {}'.format(ret['ltm']['current']['remainingTimer'], transName(ret['ltm']['next']['eventName']), transName(ret['ltm']['next']['map']))),
    ]

    # 复制器
    url = f"https://api.mozambiquehe.re/crafting?auth={APEX_AUTHKEY}"
    ret = requests.get(url=url)
    ret = ret.json()
    card_craftinfo = [
        ('title', '复制器轮换', HexToRgb(APEX_MAIN_COLOR)),
        ('separator',),
        ('subtitle', '{}'.format(transName(ret[0]['bundleContent'][0]['itemType']['name'])), HexToRgb(ret[0]['bundleContent'][0]['itemType']['rarityHex'])),
        ('subtitle', '{}'.format(transName(ret[0]['bundleContent'][1]['itemType']['name'])), HexToRgb(ret[0]['bundleContent'][1]['itemType']['rarityHex'])),
        ('subtitle', '{}'.format(transName(ret[1]['bundleContent'][0]['itemType']['name'])), HexToRgb(ret[1]['bundleContent'][0]['itemType']['rarityHex'])),
        ('subtitle', '{}'.format(transName(ret[1]['bundleContent'][1]['itemType']['name'])), HexToRgb(ret[1]['bundleContent'][1]['itemType']['rarityHex'])),
    ]

    ApexInfoCards = ResponseImage(
        primaryColor = HexToRgb(APEX_MAIN_COLOR),
        title = 'Apex 状态',
        layout = 'normal',
        width = 800,
        cardBodyFont= ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 22),
        cardSubtitleFont= ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 26),
        footer = '数据来自第三方API，复制器轮换可能有误'
    )

    ApexInfoCards.addCardList([
            ResponseImage.RichContentCard(
                raw_content = card_craftinfo 
            ),
            ResponseImage.RichContentCard(
                raw_content = card_mapinfo
            ),
        ])
    save_path = (os.path.join(SAVE_TMP_PATH, f'apex_status.png'))
    ApexInfoCards.generateImage(save_path)
    return save_path



