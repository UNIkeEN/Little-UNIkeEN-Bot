import re
import websocket
import requests, requests.exceptions, json
from utils.basicConfigs import HTTP_URL, APPLY_GROUP_ID
from utils.messageChain import MessageChain, getImgFromUrl
from PIL import Image, ImageDraw, ImageFont
from utils.basicConfigs import *
from typing import Dict, List, Union, Tuple, Any, Optional
import traceback
from utils.bufferQueue import BufferQueue
from io import BytesIO
from threading import Thread, Semaphore
import uuid

lagrangeClient = websocket.WebSocket()
lagrangeClientReturns:Dict[str, Dict[str, Any]] = {}
lagrangeClientReturnSignals:Dict[str, Semaphore] = {}

def maintainLagrangeClientReturns():
    global lagrangeClient, lagrangeClientReturns, lagrangeClientReturnSignals
    while True:
        try:
            ret = json.loads(lagrangeClient.recv())
            if not isinstance(ret, dict): continue
            echo = ret.get('echo', None)
            if echo == None: continue
            semaphore = lagrangeClientReturnSignals.get(echo, None)
            if semaphore == None: continue
            lagrangeClientReturns[echo] = ret
            semaphore.release()
        except json.JSONDecodeError as e:
            continue
        except Exception as e: 
            warning('error in maintainLagrangeClientReturns: {}'.format(e))
            break

lagrangeReturnsMaintainer = Thread(target=maintainLagrangeClientReturns)
lagrangeReturnsMaintainer.daemon = True

def sendPacketToLagrange(packet:Dict[str,Any]):
    global lagrangeClient, lagrangeClientReturns, lagrangeReturnsMaintainer
    if not lagrangeClient.connected:
        lagrangeClient.connect(HTTP_URL)
        if not lagrangeReturnsMaintainer.is_alive():
            lagrangeReturnsMaintainer.start()
    packetEncoded = json.dumps(packet, ensure_ascii=False)
    lagrangeClient.send(packetEncoded)

def get_avatar_pic(id: int)->Union[None, bytes]:
    """获取QQ头像
    @id: qq号
    @return:
        None if QQ头像获取失败
        bytes if QQ头像获取成功
    """
    url_avatar = requests.get(f'http://q2.qlogo.cn/headimg_dl?dst_uin={id}&spec=100')
    if url_avatar.status_code != requests.codes.ok:
        return None
    else:
        return url_avatar.content

def get_group_avatar_pic(id: int)->Union[None, bytes]:
    """获取群头像
    @id: 群号
    @return:
        None if 群头像获取失败
        bytes if 群头像获取成功
    """
    url_avatar = requests.get(f'https://p.qlogo.cn/gh/{id}/{id}/100/')
    if url_avatar.status_code != requests.codes.ok:
        return None
    else:
        return url_avatar.content

def parse_cqcode(cqcode:str)->Optional[Tuple[str, Dict[str,str]]]:
    """解析CQ码
    @cqcode: CQ码
    @return: 
        if cqcode不是cq码 => None
        else => (CQ码类型, {cq key: cq value})
    """
    cqcodePattern = re.compile(r'^\[(CQ\:[^\[\]\s]+)\]$')
    cqtypePattern = re.compile(r'^CQ\:([^\[\]\s\,]+)$')
    result = cqcodePattern.findall(cqcode)
    if len(result) == 0:
        print(f'cqcode = "{cqcode}"')
        print('len result == 0')
        return None
    result = result[0].split(',')
    cqtype = cqtypePattern.findall(result[0])
    if len(cqtype) == 0: 
        print('len cqtype == 0')
        return None
    cqtype = cqtype[0]
    cqdict = {}
    for r in result[1:]:
        r = r.split('=', 1)
        if len(r) != 2:
            print('len r != 2')
            return None
        cqkey, cqvalue = r
        cqdict[cqkey] = cqvalue
    return cqtype, cqdict

def gocqQuote(text:str)->str:
    """go-cqhttp文本转义
    参考链接： https://docs.go-cqhttp.org/cqcode/#%E8%BD%AC%E4%B9%89
    """
    return text.replace('&','&amp;').replace('[','&#91;').replace(']','&#93;').replace(',','&#44;')

groupSendBufferQueue = BufferQueue(1, 1) # L1 cache
groupSendBufferQueueCache = BufferQueue(3, 6) # L2 cache
groupSendBufferQueue.start()
groupSendBufferQueueCache.start()
def send(id: int, message: str, type:str='group')->None:
    """发送消息
    id: 群号或者私聊对象qq号
    message: 消息
    type: Union['group', 'private'], 默认 'group'
    """
    msgChain = MessageChain.fromCqcode(message)
    typePrint = {'group':'群', 'private': '私'}.get(type, '??')
    print(f'[{typePrint}: {id:>11d}]',msgChain)
    msgChain.removeUnsupportPiece()
    msgChain.fixLagrangeImgUrl()
    if True:
        msgChain.convertImgPathToBase64()
    if type=='group':
        packet = {
            'action': 'send_group_msg',
            'params': {
                "group_id": id,
                "message": msgChain.chain
            },
        }
        def cachedDo(packet):
            groupSendBufferQueueCache.put(sendPacketToLagrange, (packet,), )
        groupSendBufferQueue.put(cachedDo, (packet,))
    elif type=='private':
        packet = {
            'action': 'send_private_msg',
            'params': {
                "user_id": id,
                "message": msgChain.chain
            },
        }
        sendPacketToLagrange(packet)

async def aioSend(id: int, message: str, type:str='group')->None:
    raise Exception("No longer Support")

def get_group_list()->Optional[List[int]]:
    echo = str(uuid.uuid4())
    s = lagrangeClientReturnSignals[echo] = Semaphore(0)
    packet = {
        'action': 'get_group_list',
        'params': {},
        'echo': echo
    }
    sendPacketToLagrange(packet)
    if s.acquire(blocking=True, timeout=10):
        lagrangeClientReturnSignals.pop(echo)
        result = lagrangeClientReturns.pop(echo)
        return result['data']
    else:
        lagrangeClientReturnSignals.pop(echo)
        return None

def get_group_msg_history(group_id: int, message_seq: Union[int, None]=None)->list:
    raise Exception("no longer support")
    
def get_essence_msg_list(group_id: int)->list:
    raise Exception("no longer support")
    
def set_friend_add_request(flag, approve=True)->None:
    raise Exception("no longer support")
    
def get_group_file_system_info(group_id: int)->dict:
    raise Exception("no longer support")

def get_group_root_files(group_id: int)->dict:
    raise Exception("no longer support")

def get_group_files_by_folder(group_id: int, folder_id: str)->dict:
    raise Exception("no longer support")

def get_group_member_info(group_id: int, user_id: int, no_cache: bool=False)->Union[dict, None]:
    echo = str(uuid.uuid4())
    s = lagrangeClientReturnSignals[echo] = Semaphore(0)
    packet = {
        'action': 'get_group_member_info',
        'params': {
            "group_id": group_id,
            "user_id": user_id,
            "no_cache": no_cache,
        },
        'echo': echo,
    }
    sendPacketToLagrange(packet)
    if s.acquire(blocking=True, timeout=10):
        lagrangeClientReturnSignals.pop(echo)
        result = lagrangeClientReturns.pop(echo)
        return result['data']
    else:
        lagrangeClientReturnSignals.pop(echo)
        return None

def isGroupOwner(group_id:int, user_id:int)->bool:
    """判断该成员是否为群主
    @group_id: 群号
    @user_id:  待判断的成员QQ

    @return:   是否为群主
    """
    memberInfo = get_group_member_info(group_id, user_id)
    return memberInfo != None and memberInfo.get('role', '') == 'owner'


def get_group_member_list(group_id:int, no_cache:bool=False)->Union[None, dict]:
    echo = str(uuid.uuid4())
    s = lagrangeClientReturnSignals[echo] = Semaphore(0)
    packet = {
        'action': 'get_group_member_list',
        'params': {
            "group_id": group_id,
            "no_cache": no_cache,
        },
        'echo': echo,
    }
    sendPacketToLagrange(packet)
    if s.acquire(blocking=True, timeout=10):
        lagrangeClientReturnSignals.pop(echo)
        result = lagrangeClientReturns.pop(echo)
        return result['data']
    else:
        lagrangeClientReturnSignals.pop(echo)
        return None

def get_group_file_url(group_id: int, file_id: str, busid: int)-> Union[str, None]:
    raise Exception("no longer support")

def upload_group_file(group_id:int, file:str, name:str, folder:str)->None:
    raise Exception("no longer support")

def set_group_ban(group_id:int, user_id:int, duration:int)->None:
    """群组单人禁言
    @group_id: 群号
    @user_id:  用户QQ号
    @duration: 禁言时间，单位：秒
    参考链接： https://docs.go-cqhttp.org/api/#%E7%BE%A4%E7%BB%84%E5%8D%95%E4%BA%BA%E7%A6%81%E8%A8%80
    """
    packet = {
        'action': 'set_group_ban',
        'params': {
            "group_id": group_id,
            "user_id": user_id,
            "duration": duration,
        }
    }
    try:
        sendPacketToLagrange(packet)
    except BaseException as e:
        warning("base exception in set_group_ban: {}".format(e))

def get_group_system_msg()->Optional[Dict[str, List[Dict[str, Any]]]]:
    raise Exception("no longer support")

def set_group_add_request(flag: str, sub_type: str, approve: bool, reason: str="")->None:
    raise Exception("no longer support")

warningBufferQueue = BufferQueue(3, 1)
warningBufferQueue.start()

def warning(what:str)->None:
    """warning to admins"""
    stack = traceback.format_exc()
    what = '[warning]\n' + what 
    what += '\n\n[location]\n' + stack
    admin_users = WARNING_ADMIN_ID
    admin_groups = []
    # print(what)
    for admin in admin_users:
        warningBufferQueue.put(send, args=(admin, what, 'private'))
        # send(admin, what, 'private')
    for admin in admin_groups:
        warningBufferQueue.put(send, args=(admin, what, 'group'))
        # send(admin, what, 'group')

def startswith_in(msg, checklist)->bool:
    """判断字符串是否以checkList中的内容开头"""
    for i in checklist:
        if msg.startswith(i):
            return True
    return False

# 画图相关
def draw_rounded_rectangle(img, x1, y1, x2, y2, fill, r=7): 
    draw = ImageDraw.Draw(img)
    draw.ellipse((x1, y1, x1+2*r, y1+2*r), fill=fill)
    draw.ellipse((x2-2*r, y1, x2, y1+2*r), fill=fill)
    draw.ellipse((x1, y2-2*r, x1+2*r, y2), fill=fill)
    draw.ellipse((x2-2*r, y2-2*r, x2, y2), fill=fill)
    draw.rectangle((x1+r,y1,x2-r,y2),fill=fill)
    draw.rectangle((x1,y1+r,x2,y2-r),fill=fill)
    return(img)

def init_image_template(title, width, height, clr):
    img = Image.new('RGBA', (width, height), (235, 235, 235, 255))
    draw = ImageDraw.Draw(img)
    txt_size = draw.textsize(title,font=font_hywh_85w_ms)
    img = draw_rounded_rectangle(img, x1=width/2-txt_size[0]/2-15, y1=40, x2=width/2+txt_size[0]/2+15,y2=txt_size[1]+70, fill=clr)
    draw.text((width/2-txt_size[0]/2,55), title, fill=(255,255,255,255), font=font_hywh_85w_ms)
    txt_size = draw.textsize('Powered By Little-UNIkeEN-Bot',font=font_syhtmed_18)
    draw.text((width/2-txt_size[0]/2, height-50), 'Powered By Little-UNIkeEN-Bot', fill=(115,115,115,255), font = font_syhtmed_18)
    return img, draw, txt_size[1]

# 语音相关
def send_genshin_voice(sentence):
    raise Exception("no longer support")
