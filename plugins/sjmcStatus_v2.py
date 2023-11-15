from typing import Union, Any
from utils.basicEvent import *
from utils.basicConfigs import *
from utils.standardPlugin import StandardPlugin
from PIL import Image, ImageDraw, ImageFont
import requests
import base64
import re
from io import BytesIO

import aiohttp, asyncio

MINECRAFT_COLOR_CODES = {
    '0': (0, 0, 0, 255),
    '1': (0, 0, 170, 255),
    '2': (0, 170, 0, 255),
    '3': (0, 170, 170, 255),
    '4': (170, 0, 0, 255),
    '5': (170, 0, 170, 255),
    '6': (255, 170, 0, 255),
    '7': (170, 170, 170, 255),
    '8': (85, 85, 85, 255),
    '9': (85, 85, 255, 255),
    'a': (85, 255, 85, 255),
    'b': (85, 255, 255, 255),
    'c': (255, 85, 85, 255),
    'd': (255, 85, 255, 255),
    'e': (255, 255, 85, 255),
    'f': (255, 255, 255, 255),
}

class ShowSjmcStatus(StandardPlugin):
    def __init__(self) -> None:
        self.server_groups = {
            '-mc' : '',
            '-sjmc' : 'SJMC',
            '-fdc' : 'FDCraft',
            '-tjmc' : 'TJMC',
            '-xjtumc': 'XJTUMC',
        }
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg in self.server_groups.keys()
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        server_group = self.server_groups[msg]
        send(target, f"正在获取{server_group}服务器状态...", data['message_type'])
        try:
            imgPath = draw_sjmc_info(aio_get_sjmc_info(server_group), server_group)
            imgPath = imgPath if os.path.isabs(imgPath) else os.path.join(ROOT_PATH, imgPath)
            send(target, '[CQ:image,file=files:///%s]'%imgPath, data['message_type'])
        except BaseException as e:
            send(target, "internal error while getting sjmc", data['message_type'])
            warning("basic exception in ShowSjmcStatus: {}".format(e))
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'ShowSjmcStatus',
            'description': 'mc服务器状态[SJMC/FDC/TJMC/XJTUMC]',
            'commandDescription': '/'.join(self.server_groups.keys()),
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
def fetch_server_list(group)->Union[None, Dict[str, Any]]:
    url=f"https://mc.sjtu.cn/custom/serverlist/?list={group}"
    server_list = []
    try:
        res = requests.get(url, verify=False)
        if res.status_code!= requests.codes.ok:
            return None
        server_list = res.json()
        for server in server_list:
            if 'ip' not in server:
                return None
        return server_list
    except requests.JSONDecodeError as e:
        warning("sjmc json decode error: {}".format(e))
    except requests.Timeout as e:
        print("connection time out")
    except BaseException as e:
        warning("sjmc basic exception: {}".format(e))
def aio_get_sjmc_info(group=""):
    async def get_page(i, addr):
        url=f"https://mc.sjtu.cn/custom/serverlist/?query={addr}"
        async with aiohttp.request('GET', url) as req:
            status = await req.json()
            return i, status
    server_list = fetch_server_list(group)
    loop = asyncio.new_event_loop()
    tasks = [loop.create_task(get_page(i, server['ip'])) for i, server in enumerate(server_list)]
    result = loop.run_until_complete(asyncio.wait(tasks))
    loop.close()
    result = [r.result() for r in result[0]]
    result = sorted(result, key=lambda x: x[0])
    result = [r[1] for r in result]
    return result
def get_sjmc_info():
    url="https://mc.sjtu.cn/wp-admin/admin-ajax.php"
    dat = []
    for t in range(8):
        #try:
        params={
            "_ajax_nonce": "0e441f8c8a",
            "action": "fetch_mcserver_status",
            "i": str(t),
        }
        try:
            res = requests.get(url, verify=False, params=params)
            if res.status_code!= requests.codes.ok:
                continue
            res = res.json()
            dat.append(res)
        except requests.JSONDecodeError as e:
            warning("sjmc json decode error: {}".format(e))
        except requests.Timeout as e:
            print("connection time out")
        except KeyError as e:
            warning("key error in sjmc: {}".format(e))
        except BaseException as e:
            warning("sjmc basic exception: {}".format(e))
    return dat

def draw_sjmc_info(dat, server_group):
    if server_group == '':
        server_group = 'MC'
    j = sum([res['online'] and res['players']['online']!=0 for res in dat])
    j1 = 0
    FONTS_PATH = 'resources/fonts'
    white, grey, green, red = (255,255,255,255),(128,128,128,255),(0,255,33,255),(255,85,85,255)
    font_mc_l = ImageFont.truetype(os.path.join(FONTS_PATH, 'Minecraft AE.ttf'), 30)
    font_mc_m = ImageFont.truetype(os.path.join(FONTS_PATH, 'Minecraft AE.ttf'), 20)
    font_mc_s = ImageFont.truetype(os.path.join(FONTS_PATH, 'Minecraft AE.ttf'), 16)
    font_mc_xl = ImageFont.truetype(os.path.join(FONTS_PATH, 'Minecraft AE.ttf'), 39)
    width=860
    height=215+len(dat)*140+j*35
    img = Image.new('RGBA', (width, height), (46, 33, 23, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 120, width, height-80), fill=(15, 11, 7, 255))
    draw.text((width-140-draw.textsize(f"{server_group}服务器状态", font=font_mc_xl)[0],42), 
        f"{server_group}服务器状态", fill=(255,255,255,255), font=font_mc_xl)
    draw.text((width-120,44), "LITTLE\nUNIkeEN", fill=(255,255,255,255), font=font_syht_m)
    
    # 绘制带颜色标题
    def draw_colored_title(draw, text, position, font, default_color=(255, 255, 255, 255)):
        x, y = position
        current_color = default_color
        buffer_text = ''
        i = 0
        while i < len(text):
            if text[i] == '§':
                if buffer_text:
                    draw.text((x, y), buffer_text, fill=current_color, font=font)
                    size = draw.textsize(buffer_text, font=font)
                    x += size[0]
                    buffer_text = ''
                if i + 1 < len(text) and text[i+1].lower() in MINECRAFT_COLOR_CODES:
                    current_color = MINECRAFT_COLOR_CODES.get(text[i+1].lower(), default_color)
                i += 2  
            else:
                buffer_text += text[i]
                i += 1          
        if buffer_text:
            draw.text((x, y), buffer_text, fill=current_color, font=font)
            
    for i, res in enumerate(dat):
        fy = 160 + i*140 + j1*31
        try:
            title = res['description']
            if not isinstance(title, str):
                title = title['text']
            title = re.sub(r'§[klmnor]', '', title)
            title = title.replace('|',' | ',1)
            title = title.replace('\n','  |  ',1)
            title = title.replace('服务器已离线...', '')
        except:
            title = 'Unknown Server Name'
        draw_colored_title(draw, title, (160, fy), font=font_mc_l)

        # 绘制图标
        try:
            icon_url = res['favicon']
            if icon_url[:4]=="data":
                img_avatar = Image.open(decode_image(icon_url)).resize((80,80))
                if img_avatar != None:
                    img.paste(img_avatar, (60, fy))
            else:
                url_avatar = requests.get(icon_url)
                if url_avatar.status_code != requests.codes.ok:
                    img_avatar = None
                else:
                    img_avatar = Image.open(BytesIO(url_avatar.content)).resize((80,80))
                    img.paste(img_avatar, (60, fy))
        except KeyError as e:
            warning("key error in sjmc draw icon: {}".format(e))
        except BaseException as e:
            warning("base exception in sjmc draw icon: {}".format(e))

        if res['online']:
            res['hostname'] = res['hostname'].replace('.',' . ')
            if 'port' in res.keys() and res['port'] != None:
                port = str(res['port']).strip()
                if port != '25565':
                    res['hostname'] += ' : ' + port
            draw.text((160, fy+45), res['hostname'], fill=grey, font=font_mc_m)
            txt_size = draw.textsize(f"{res['ping']}ms", font=font_mc_m)
            ping = int(res['ping'])
            clr = red if ping>=100 else green
            draw.text((width-60-txt_size[0], fy), f"{res['ping']}ms", fill=clr, font=font_mc_m)
            txt_size = draw.textsize(f"{res['players']['online']}/{res['players']['max']}", font=font_mc_m)
            draw.text((width-60-txt_size[0], fy+32), f"{res['players']['online']}/{res['players']['max']}", fill=grey, font=font_mc_m)
            txt_size = draw.textsize(res['version'], font=font_mc_m)
            draw.text((width-60-txt_size[0], fy+64), res['version'], fill=grey, font=font_mc_m)
            if res['players']['online']!=0:
                j1 += 1
                txt_plr = ""
                try:
                    for player in res['players']['sample']:
                        if draw.textsize(txt_plr+player['name']+'、',font=font_mc_s)[0]>= width-300:
                            txt_plr = txt_plr[:-1]+'等 '
                            break
                        txt_plr += (player['name']+'、')
                    txt_plr = txt_plr[:-1]+' 正在游玩'
                except:
                    txt_plr = '( 玩家信息获取失败qwq )'
                txt_size = draw.textsize(txt_plr, font=font_mc_s)
                txt_size_2 = draw.textsize('●', font=font_mc_s)
                draw.text((width-68-txt_size[0]-txt_size_2[0], fy+96), txt_plr, fill=grey, font=font_mc_s)
                draw.text((width-60-txt_size_2[0], fy+96), '●', fill=green, font=font_mc_s)
        else:
            txt_size = draw.textsize("offline", font=font_mc_m)
            draw.text((width-60-txt_size[0], fy), "offline", fill=red, font=font_mc_m)
            txt_size = draw.textsize("服务器离线", font=font_mc_m)
            draw.text((width-60-txt_size[0], fy+32), "服务器离线", fill=grey, font=font_mc_m)
    draw.text((60,height-50),"欢迎加入SJTU-Minecraft交流群！群号 712514518",fill=white,font=font_mc_m)
    save_path=os.path.join(SAVE_TMP_PATH,'sjmc_status_{}.png'.format(server_group))
    img.save(save_path)
    return save_path

def decode_image(src)->Union[None, BytesIO]:
    """
    解码图片
    :param src: 图片编码
        eg:
            src="data:image/gif;base64,R0lGODlhMwAxAIAAAAAAAP///
                yH5BAAAAAAALAAAAAAzADEAAAK8jI+pBr0PowytzotTtbm/DTqQ6C3hGX
                ElcraA9jIr66ozVpM3nseUvYP1UEHF0FUUHkNJxhLZfEJNvol06tzwrgd
                LbXsFZYmSMPnHLB+zNJFbq15+SOf50+6rG7lKOjwV1ibGdhHYRVYVJ9Wn
                k2HWtLdIWMSH9lfyODZoZTb4xdnpxQSEF9oyOWIqp6gaI9pI1Qo7BijbF
                ZkoaAtEeiiLeKn72xM7vMZofJy8zJys2UxsCT3kO229LH1tXAAAOw=="

    :return: 图片的BytesIO
    """
    # 1、信息提取
    result = re.search("data:image/(?P<ext>.*?);base64,(?P<data>.*)", src, re.DOTALL)
    if result:
        ext = result.groupdict().get("ext")
        data = result.groupdict().get("data")
    else:
        return None
    # 2、base64解码
    return BytesIO(base64.urlsafe_b64decode(data))