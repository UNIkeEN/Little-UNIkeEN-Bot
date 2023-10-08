from typing import Union, Any
from utils.basic_event import *
from utils.basic_configs import *
from utils.standard_plugin import StandardPlugin
from utils.config_api import get_group_admins
from utils.response_image import *
from PIL import Image, ImageDraw, ImageFont
import requests
import base64
import re
from io import BytesIO
from utils.sql_utils import new_sql_session
from threading import Semaphore

import aiohttp, asyncio


def create_mcs_sql():
    mydb, mycursor = new_sql_session()
    mycursor.execute("""
    create table if not exists `mcServerStatus` (
        `group_id` bigint unsigned not null comment '群号',
        `server` char(64) not null default '' comment '服务器ip',
        primary key(`group_id`, `server`)
    )""")


def get_server_list(group_id: str) -> List[str]:
    mydb, mycursor = new_sql_session()
    mycursor.execute("""
    select `server` from `mcServerStatus`
    where `group_id` = %s""", (group_id,))
    result = list(mycursor)
    return [server for server, in result]


def add_server(group_id: int, server: str) -> bool:
    mydb, mycursor = new_sql_session()
    mycursor.execute("""
    replace into `mcServerStatus` (`group_id`, `server`)
    values (%s, %s)""", (group_id, server))
    return True


def remove_server(group_id: int, server: str) -> Tuple[bool, str]:
    mydb, mycursor = new_sql_session()
    mycursor.execute("""select count(*) from `mcServerStatus`
    where `group_id` = %s and `server` = %s
    """, (group_id, server))
    if list(mycursor)[0][0] == 0:
        return False, '本群尚未添加服务器“%s”' % server
    mycursor.execute("""delete from `mcServerStatus`
    where `group_id` = %s and `server` = %s
    """, (group_id, server))
    return True, '移除成功'


def create_mcs_footer_sql():
    mydb, mycursor = new_sql_session()
    mycursor.execute("""
    create table if not exists `mcServerStatusFooter` (
        `group_id` bigint unsigned not null comment '群号',
        `footer` varchar(256) not null default '' comment 'footer',
        primary key(`group_id`)
    )""")


def get_footer(group_id: str) -> List[str]:
    mydb, mycursor = new_sql_session()
    mycursor.execute("""
    select `footer` from `mcServerStatusFooter`
    where `group_id` = %s""", (group_id,))
    result = list(mycursor)
    if len(result) > 0:
        result = result[0][0]
    else:
        result = ''
    return result


def set_footer(group_id: int, footer: str) -> bool:
    mydb, mycursor = new_sql_session()
    mycursor.execute("""
    replace into `mcServerStatusFooter` (`group_id`, `footer`)
    values (%s, %s)""", (group_id, footer))
    return True


def remove_footer(group_id: int) -> Tuple[bool, str]:
    mydb, mycursor = new_sql_session()
    mycursor.execute("""select count(*) from `mcServerStatusFooter`
    where `group_id` = %s
    """, (group_id,))
    if list(mycursor)[0][0] == 0:
        return False, '尚未设置footer'
    mycursor.execute("""delete from `mcServerStatusFooter`
    where `group_id` = %s
    """, (group_id,))
    return True, '移除成功'


class ShowMcStatus(StandardPlugin):
    def judge_trigger(self, msg: str, data: Any) -> bool:
        return msg == '-mcs' or msg == '-mcsip'

    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        group_id = data['group_id']
        server_list = get_server_list(group_id)
        if msg == '-mcs':
            if len(server_list) == 0:
                send(group_id, f"本群尚未添加Minecraft服务器", data['message_type'])
                return 'OK'
            send(group_id, f"正在获取Minecraft服务器状态...", data['message_type'])
            try:
                imgPath = draw_sjmc_info(aio_get_sjmc_info(server_list), group_id)
                imgPath = imgPath if os.path.isabs(imgPath) else os.path.join(ROOT_PATH, imgPath)
                send(group_id, '[CQ:image,file=files:///%s]' % imgPath, data['message_type'])
            except BaseException as e:
                send(group_id, "internal error while getting Minecraft server status", data['message_type'])
                warning("basic exception in ShowSjmcStatus: {}".format(e))
            return "OK"
        else:
            if len(server_list) == 0:
                send(group_id, f"本群尚未添加Minecraft服务器", data['message_type'])
                return 'OK'
            try:
                imgPath = draw_server_ip_list(server_list)
                imgPath = imgPath if os.path.isabs(imgPath) else os.path.join(ROOT_PATH, imgPath)
                send(group_id, '[CQ:image,file=files:///%s]' % imgPath, data['message_type'])
            except BaseException as e:
                send(group_id, "internal error while getting Minecraft server status", data['message_type'])
                warning("basic exception in ShowSjmcStatus: {}".format(e))
            return "OK"

    def get_plugin_info(self, ) -> Any:
        return {
            'name': 'ShowSjmcStatusV3',
            'description': 'mc服务器状态',
            'commandDescription': '-mcs',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': ['mcServerStatus'],
            'version': '1.0.0',
            'author': 'Unicorn',
        }


class McStatusRemoveServer(StandardPlugin):
    def __init__(self):
        self.triggerPattern = re.compile(r'^-mcsrm\s+(\S+)')

    def judge_trigger(self, msg: str, data: Any) -> bool:
        return self.triggerPattern.match(msg) != None

    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        groupId = data['group_id']
        userId = data['user_id']
        admins = set(u['user_id'] for u in get_group_member_list(groupId) if u['role'] in ['admin', 'owner']).union(
            get_group_admins(groupId)
        )
        if userId not in admins:
            send(groupId, '[CQ:reply,id=%d]权限检查失败。该指令仅允许群管理员触发。' % data['message_id'],
                 data['message_type'])
            return 'OK'
        server = self.triggerPattern.findall(msg)[0]
        succ, result = remove_server(groupId, server)
        send(groupId, '[CQ:reply,id=%d]%s' % (data['message_id'], result))
        return 'OK'

    def get_plugin_info(self) -> Any:
        return {
            'name': 'McStatusRemoveServer',
            'description': '移除群聊可查询Minecraft服务器',
            'commandDescription': '-mcsrm [server IP]',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': ['mcServerStatus'],
            'version': '1.0.0',
            'author': 'Unicorn',
        }


class McStatusAddServer(StandardPlugin):
    initGuard = Semaphore()

    def __init__(self):
        if self.initGuard.acquire(blocking=False):
            create_mcs_sql()
        self.triggerPattern = re.compile(r'^-mcsadd\s+(\S+)')

    def judge_trigger(self, msg: str, data: Any) -> bool:
        return self.triggerPattern.match(msg) != None

    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        groupId = data['group_id']
        userId = data['user_id']
        admins = set(u['user_id'] for u in get_group_member_list(groupId) if u['role'] in ['admin', 'owner']).union(
            get_group_admins(groupId)
        )
        if userId not in admins:
            send(groupId, '[CQ:reply,id=%d]权限检查失败。该指令仅允许群管理员触发。' % data['message_id'],
                 data['message_type'])
            return 'OK'
        server = self.triggerPattern.findall(msg)[0]
        if len(server) > 64:  # do some check
            send(groupId, '[CQ:reply,id=%d]添加失败，IP最长为64字符。' % data['message_id'])
        else:
            succ = add_server(groupId, server)
            if succ:
                send(groupId, '[CQ:reply,id=%d]添加成功' % data['message_id'])
            else:
                send(groupId, '[CQ:reply,id=%d]添加失败：未知错误，请联系管理员。' % data['message_id'])
        return 'OK'

    def get_plugin_info(self) -> Any:
        return {
            'name': 'McStatusAddServer',
            'description': '添加群聊可查询Minecraft服务器',
            'commandDescription': '-mcsadd [server IP]',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': ['mcServerStatus'],
            'version': '1.0.0',
            'author': 'Unicorn',
        }


class McStatusRemoveFooter(StandardPlugin):
    def judge_trigger(self, msg: str, data: Any) -> bool:
        return msg == '-mcsrmfooter'

    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        groupId = data['group_id']
        userId = data['user_id']
        admins = set(u['user_id'] for u in get_group_member_list(groupId) if u['role'] in ['admin', 'owner']).union(
            get_group_admins(groupId)
        )
        if userId not in admins:
            send(groupId, '[CQ:reply,id=%d]权限检查失败。该指令仅允许群管理员触发。' % data['message_id'],
                 data['message_type'])
            return 'OK'
        succ, result = remove_footer(groupId)
        send(groupId, '[CQ:reply,id=%d]%s' % (data['message_id'], result))
        return 'OK'

    def get_plugin_info(self) -> Any:
        return {
            'name': 'McStatusRemoveFooter',
            'description': '移除群聊mcs列表底部文字',
            'commandDescription': '-mcsrmfooter',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': ['mcServerStatusFooter'],
            'version': '1.0.0',
            'author': 'Unicorn',
        }


class McStatusSetFooter(StandardPlugin):
    initGuard = Semaphore()

    def __init__(self):
        if self.initGuard.acquire(blocking=False):
            create_mcs_footer_sql()
        self.triggerPattern = re.compile(r'^-mcssetfooter\s+(\S+)')

    def judge_trigger(self, msg: str, data: Any) -> bool:
        return self.triggerPattern.match(msg) != None

    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        groupId = data['group_id']
        userId = data['user_id']
        admins = set(u['user_id'] for u in get_group_member_list(groupId) if u['role'] in ['admin', 'owner']).union(
            get_group_admins(groupId)
        )
        if userId not in admins:
            send(groupId, '[CQ:reply,id=%d]权限检查失败。该指令仅允许群管理员触发。' % data['message_id'],
                 data['message_type'])
            return 'OK'
        footer = self.triggerPattern.findall(msg)[0]
        if len(footer) > 256:  # do some check
            send(groupId, '[CQ:reply,id=%d]添加失败，IP最长为256字符。' % data['message_id'])
        else:
            succ = set_footer(groupId, footer)
            if succ:
                send(groupId, '[CQ:reply,id=%d]添加成功' % data['message_id'])
            else:
                send(groupId, '[CQ:reply,id=%d]添加失败：未知错误，请联系管理员。' % data['message_id'])
        return 'OK'

    def get_plugin_info(self) -> Any:
        return {
            'name': 'McStatusSetFooter',
            'description': '设置群聊mcs列表底部文字',
            'commandDescription': '-mcssetfooter [footer]',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': ['mcServerStatusFooter'],
            'version': '1.0.0',
            'author': 'Unicorn',
        }


def aio_get_sjmc_info(server_list: List[str]):
    # print(server_list)
    async def get_page(i, addr):
        url = f"https://mc.sjtu.cn/custom/serverlist/?query={addr}"
        async with aiohttp.request('GET', url) as req:
            status = await req.json()
            if 'hostname' not in status.keys():
                status['hostname'] = addr
            return i, status

    loop = asyncio.new_event_loop()
    tasks = [loop.create_task(get_page(i, server)) for i, server in enumerate(server_list)]
    result = loop.run_until_complete(asyncio.wait(tasks))
    loop.close()
    result = [r.result() for r in result[0]]
    result = sorted(result, key=lambda x: x[0])
    result = [r[1] for r in result]
    # print(result)
    return result


def draw_sjmc_info(dat, group_id: int):
    j = sum([res['online'] and res['players']['online'] != 0 for res in dat])
    j1 = 0
    footer = get_footer(group_id)
    FONTS_PATH = 'resources/fonts'
    white, grey, green, red = (255, 255, 255, 255), (128, 128, 128, 255), (0, 255, 33, 255), (255, 85, 85, 255)
    font_mc_l = ImageFont.truetype(os.path.join(FONTS_PATH, 'Minecraft AE.ttf'), 30)
    font_mc_m = ImageFont.truetype(os.path.join(FONTS_PATH, 'Minecraft AE.ttf'), 20)
    font_mc_s = ImageFont.truetype(os.path.join(FONTS_PATH, 'Minecraft AE.ttf'), 16)
    font_mc_xl = ImageFont.truetype(os.path.join(FONTS_PATH, 'Minecraft AE.ttf'), 39)
    width = 860
    height = 215 + len(dat) * 140 + j * 35 + 60
    if len(footer) == 0:
        height -= 80 - 20
    img = Image.new('RGBA', (width, height), (46, 33, 23, 255))
    draw = ImageDraw.Draw(img)
    if len(footer) > 0:
        draw.rectangle((0, 120, width, height - 80 - 40), fill=(15, 11, 7, 255))
    else:
        draw.rectangle((0, 120, width, height - 60), fill=(15, 11, 7, 255))
    draw.text((width - 140 - draw.textsize(f"Minecraft服务器状态", font=font_mc_xl)[0], 42),
              f"Minecraft服务器状态", fill=(255, 255, 255, 255), font=font_mc_xl)
    draw.text((width - 120, 44), "LITTLE\nUNIkeEN", fill=(255, 255, 255, 255), font=font_syht_m)

    for i, res in enumerate(dat):
        fy = 160 + i * 140 + j1 * 31
        # 处理title非法字符
        try:
            title = res['description']
            if not isinstance(title, str):
                title = title['text']
            title = title.replace('|', ' | ', 1)
            title = title.replace('\n', '  |  ', 1)
            title = title.replace('§l', '', 5)
            title = title.replace('§e', '', 5)
            title = title.replace('§n', '', 5)
            title = title.replace('服务器已离线...', '')
        except:
            title = 'Unknown'
        # cop = re.compile("[^\u4e00-\u9fa5^a-z^A-Z^0-9^|^\ ^-]") # 正则筛选
        # title = cop.sub("", title)

        # draw icon
        try:
            icon_url = res['favicon']
            if icon_url[:4] == "data":
                img_avatar = Image.open(decode_image(icon_url)).resize((80, 80))
                if img_avatar != None:
                    img.paste(img_avatar, (60, fy))
            else:
                url_avatar = requests.get(icon_url)
                if url_avatar.status_code != requests.codes.ok:
                    img_avatar = None
                else:
                    img_avatar = Image.open(BytesIO(url_avatar.content)).resize((80, 80))
                    img.paste(img_avatar, (60, fy))
        except KeyError as e:
            warning("key error in sjmc draw icon: {}".format(e))
        except BaseException as e:
            warning("base exception in sjmc draw icon: {}".format(e))

        new_title = title
        if res['online']:
            res['hostname'] = res['hostname'].replace('.', ' . ')
            if 'port' in res.keys() and res['port'] != None:
                port = str(res['port']).strip()
                if port != '25565':
                    res['hostname'] += ' : ' + port
        draw.text((160, fy), new_title, fill=white, font=font_mc_l)
        draw.text((160, fy + 45), res['hostname'], fill=grey, font=font_mc_m)
        if res['online']:
            txt_size = draw.textsize(f"{res['ping']}ms", font=font_mc_m)
            ping = int(res['ping'])
            clr = red if ping >= 100 else green
            draw.text((width - 60 - txt_size[0], fy), f"{res['ping']}ms", fill=clr, font=font_mc_m)
            txt_size = draw.textsize(f"{res['players']['online']}/{res['players']['max']}", font=font_mc_m)
            draw.text((width - 60 - txt_size[0], fy + 32), f"{res['players']['online']}/{res['players']['max']}",
                      fill=grey, font=font_mc_m)
            txt_size = draw.textsize(res['version'], font=font_mc_m)
            draw.text((width - 60 - txt_size[0], fy + 64), res['version'], fill=grey, font=font_mc_m)
            if res['players']['online'] != 0:
                j1 += 1
                txt_plr = ""
                try:
                    for player in res['players']['sample']:
                        if draw.textsize(txt_plr + player['name'] + '、', font=font_mc_s)[0] >= width - 300:
                            txt_plr = txt_plr[:-1] + '等 '
                            break
                        txt_plr += (player['name'] + '、')
                    txt_plr = txt_plr[:-1] + ' 正在游玩'
                except:
                    txt_plr = '( 玩家信息获取失败qwq )'
                txt_size = draw.textsize(txt_plr, font=font_mc_s)
                txt_size_2 = draw.textsize('●', font=font_mc_s)
                draw.text((width - 68 - txt_size[0] - txt_size_2[0], fy + 96), txt_plr, fill=grey, font=font_mc_s)
                draw.text((width - 60 - txt_size_2[0], fy + 96), '●', fill=green, font=font_mc_s)
        else:
            txt_size = draw.textsize("offline", font=font_mc_m)
            draw.text((width - 60 - txt_size[0], fy), "offline", fill=red, font=font_mc_m)
            txt_size = draw.textsize("服务器离线", font=font_mc_m)
            draw.text((width - 60 - txt_size[0], fy + 32), "服务器离线", fill=grey, font=font_mc_m)
    if len(footer) > 0:
        draw.text((60, height - 50 - 40), footer, fill=white, font=font_mc_m)
    draw.text((width / 2, height - 30), "Powered by LITTLE-UNIkeEN@SJMC", fill=(200, 200, 200, 255), font=font_syht_m,
              anchor="mm")
    save_path = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'mc_server_status_%d.png' % group_id)
    img.save(save_path)
    return save_path


def decode_image(src) -> Union[None, BytesIO]:
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


def draw_server_ip_list(server_list: List[str]) -> str:
    img = ResponseImage(
        theme='unicorn',
        title='服务器IP列表',
        titleColor=PALETTE_SJTU_BLUE,
        primaryColor=PALETTE_SJTU_RED,
        layout='normal')

    img.add_card(
        ResponseImage.NormalCard(
            body='\n'.join(server_list),
        )
    )
    save_path = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'mc_server_list.png')
    img.generate_image(save_path)
    return save_path
