from datetime import datetime
from typing import Union, Any
from utils.basicEvent import *
from utils.basicConfigs import *
from utils.standardPlugin import StandardPlugin
from PIL import Image, ImageDraw, ImageFont
import requests
import base64
import re
import uuid
from io import BytesIO

class ShowSjmcStatus(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg == '-sjmc'
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        send(target, '正在获取sjmc状态...', data['message_type'])
        imgPath = get_sjmc_info()
        imgPath = imgPath if os.path.isabs(imgPath) else os.path.join(ROOT_PATH, imgPath)
        send(target, '[CQ:image,file=files://%s,id=40000]'%imgPath, data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'ShowSjmcStatus',
            'description': 'mc服务器状态',
            'commandDescription': '-sjmc',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
def get_sjmc_info():
    url="https://mc.sjtu.cn/wp-admin/admin-ajax.php"
    dat = []
    j, j1=0, 0
    for t in range(7):
        #try:
        params={
            "_ajax_nonce": "0e441f8c8a",
            "action": "fetch_mcserver_status",
            "i": str(t)
        }
        try:
            res = requests.get(url, params=params)
            if res.status_code!= requests.codes.ok:
                continue
            res = res.json()
            if res['online'] and res['players']['online']!=0:
                j+=1
            dat.append(res)
        except requests.JSONDecodeError as e:
            warning("sjmc json decode error: {}".format(e))
        except requests.Timeout as e:
            print("connection time out")
        except KeyError as e:
            warning("key error in sjmc: {}".format(e))
        except BaseException as e:
            warning("sjmc basic exception: {}".format(e))
    FONTS_PATH = 'resources/fonts'
    white, grey, green, red = (255,255,255,255),(128,128,128,255),(0,255,33,255),(255,85,85,255)
    font_mc_l = ImageFont.truetype(os.path.join(FONTS_PATH, 'Minecraft AE.ttf'), 30)
    font_mc_m = ImageFont.truetype(os.path.join(FONTS_PATH, 'Minecraft AE.ttf'), 20)
    font_mc_s = ImageFont.truetype(os.path.join(FONTS_PATH, 'Minecraft AE.ttf'), 16)
    font_mc_xl = ImageFont.truetype(os.path.join(FONTS_PATH, 'Minecraft AE.ttf'), 39)
    width=860
    height=1225+j*35
    img = Image.new('RGBA', (width, height), (46, 33, 23, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 120, width, height-80), fill=(15, 11, 7, 255))
    draw.text((width-460,42), "SJMC服务器状态", fill=(255,255,255,255), font=font_mc_xl)
    draw.text((width-120,44), "LITTLE\nUNIkeEN", fill=(255,255,255,255), font=font_syht_m)
    
    for i in range(len(dat)):
        fy = 160+i*140+j1*31
        res = dat[i]
        # 处理title非法字符
        try:
            title = res['description']['text']
            title = title.replace('|',' | ',1)
            title = title.replace('\n','  |  ',1)
            title = title.replace('§l','',5)
            title = title.replace('§e','',5)
            title = title.replace('§n','',5)
            title = title.replace('服务器已离线...', '')
        except:
            title = 'Unknown'
        # cop = re.compile("[^\u4e00-\u9fa5^a-z^A-Z^0-9^|^\ ^-]") # 正则筛选
        # title = cop.sub("", title)

        icon_url = res['favicon']
        if icon_url[:4]=="data":
            img_avatar = Image.open(decode_image(icon_url)).resize((80,80))
        else:
            url_avatar = requests.get(icon_url)
            img_avatar = Image.open(BytesIO(url_avatar.content)).resize((80,80))
        img.paste(img_avatar, (60, fy))
        new_title=""
        m=0
        while True:
            if title[m]=='§':
                m+=2
            new_title+=title[m]
            m+=1
            if m>=len(title):
                break
        if res['online']:
            res['hostname'] = res['hostname'].replace('.',' . ')
        draw.text((160, fy), new_title, fill=white, font=font_mc_l)
        if res['online']:
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
    save_path=os.path.join(SAVE_TMP_PATH,'sjmc_status.png')
    img.save(save_path)
    return save_path

def decode_image(src):
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

    :return: str 保存到本地的文件名
    """
    # 1、信息提取
    result = re.search("data:image/(?P<ext>.*?);base64,(?P<data>.*)", src, re.DOTALL)
    if result:
        ext = result.groupdict().get("ext")
        data = result.groupdict().get("data")
    else:
        raise Exception("Do not parse!")
    # 2、base64解码
    img = base64.urlsafe_b64decode(data)
    # 3、二进制文件保存
    filename = os.path.join(SAVE_TMP_PATH, "{}.{}".format(uuid.uuid4(), ext))
    with open(filename, "wb") as f:
        f.write(img)
    return filename
