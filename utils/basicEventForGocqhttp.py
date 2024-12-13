import re
import mysql.connector
import requests, requests.exceptions, json
from utils.basicConfigs import HTTP_URL, APPLY_GROUP_ID
from PIL import Image, ImageDraw, ImageFont
from utils.basicConfigs import *
import time
import random
from typing import Dict, List, Union, Tuple, Any, Optional
from pymysql.converters import escape_string
import traceback
import aiohttp, asyncio
from utils.bufferQueue import BufferQueue
from io import BytesIO
from utils.messageChain import MessageChain, getImgFromUrl

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

def get_login_info()->dict:
    """获取登录号信息
    @return: {
        'nickname': QQ昵称,
        'user_id':  QQ号
    }
    """
    url = HTTP_URL+"/get_login_info"
    try:
        loginInfo = requests.get(url).json()
        if loginInfo['status'] != 'ok':
            warning("get_login_info requests not return ok")
            return []
        return loginInfo['data']
    except requests.JSONDecodeError as e:
        warning("error in get_login_info: {}".format(e))
    except KeyError as e:
        warning("key error in get_login_info: {}".format(e))
    return 0, ''

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
    url = HTTP_URL+"/send_msg"
    if type=='group':
        params = {
            "message_type": type,
            "group_id": id,
            "message": message
        }
        def cachedDo(url, params):
            groupSendBufferQueueCache.put(requests.get, (url,), {'params':params})
        groupSendBufferQueue.put(cachedDo, (url, params))
        # requests.get(url, params=params)
    elif type=='private':
        params = {
            "message_type": type,
            "user_id": id,
            "message": message
        }
        requests.get(url, params=params)

    print(params)
    # ###
    # pic=(re.findall("file:///(.*?)]",message))
    # if len(pic)!=0:
    #     try:
    #         for f in pic:      
    #             img=Image.open(f)
    #             img.convert('L').save(f)
    #     except:
    #         pass
    # pic=(re.findall("file:///(.*?),",message))
    # if len(pic)!=0:
    #     try:
    #         for f in pic:      
    #             img=Image.open(f)
    #             img.convert('L').save(f)
    #     except:
    #         pass
    # ###
async def aioSend(id: int, message: str, type:str='group')->None:
    """异步发送消息
    id: 群号或者私聊对象qq号
    message: 消息
    type: Union['group', 'private'], 默认 'group'
    """
    url = HTTP_URL+"/send_msg"
    if type=='group':
        params = {
            "message_type": type,
            "group_id": id,
            "message": message
        }
    elif type=='private':
        params = {
            "message_type": type,
            "user_id": id,
            "message": message
        }
    async with aiohttp.request('GET', url, params=params) as req:
        pass

def get_group_list()->list:
    """获取群聊列表
    @return:
        [
            {
                'group_create_time': int,
                'group_id': int,
                'group_name': str,
                'group_level': int,
                'max_member_count': int,
                'member_count': int,
            },
            ....
        ]
    参考链接： https://docs.go-cqhttp.org/api/#%E8%8E%B7%E5%8F%96%E7%BE%A4%E5%88%97%E8%A1%A8
    """
    url = HTTP_URL+"/get_group_list"
    try:
        groupList = json.loads(requests.get(url).text)
        if groupList['status'] != 'ok':
            warning("get_group_list requests not return ok")
            return []
        return groupList['data']
    except BaseException as e:
        warning("error in get_group_list, error: {}".format(e))
        return []

def get_group_msg_history(group_id: int, message_seq: Union[int, None]=None)->list:
    """获取群消息历史记录
    @message_seq:
        起始消息序号, 可通过 get_msg 获得
        如果是None将默认获取最新的消息
    @group_id: 群号
    @return: 从起始序号开始的前19条消息
    参考链接： https://docs.go-cqhttp.org/api/#%E8%8E%B7%E5%8F%96%E7%BE%A4%E6%B6%88%E6%81%AF%E5%8E%86%E5%8F%B2%E8%AE%B0%E5%BD%95
    """
    url = HTTP_URL+"/get_group_msg_history"
    try:
        params = {
            "group_id": group_id
        }
        if message_seq != None:
            params["message_seq"] = message_seq
            
        messageHistory = requests.get(url, params=params).json()
        if messageHistory['status'] != 'ok':
            if messageHistory['msg'] == 'MESSAGES_API_ERROR' or messageHistory['msg'] == 'GROUP_INFO_API_ERROR':
                print("group {} meet '{}' error".format(group_id, messageHistory['msg']))
            else:
                warning("get_group_msg_history requests not return ok\nmessages = {}\ngroup_id={}\nmessage_seq={}".format(
                messageHistory, group_id, message_seq))
            return []
        return messageHistory['data']['messages']
    except requests.JSONDecodeError as e:
        warning('json decode error in get_group_msg_history: {}'.format(e))
    except BaseException as e:
        warning('error in get_group_msg_history, error: {}'.format(e))
    return []
def get_essence_msg_list(group_id: int)->list:
    """获取精华消息列表
    @group_id:  群号
    @return:    精华消息列表
    """
    url = HTTP_URL+"/get_essence_msg_list"
    try:
        params = {
            "group_id": group_id
        }
        essenceMsgs = requests.get(url, params=params).json()
        if essenceMsgs['status'] != 'ok':
            warning("get_essence_msg_list requests not return ok")
            return []
        return essenceMsgs['data']
    except requests.JSONDecodeError as e:
        warning("json decode error in get_essence_msg_list: {}".format(e))
    except BaseException as e:
        warning("error in get_essence_msg_list, error: {}".format(e))
    return []
def set_friend_add_request(flag:str, approve:bool=True, remark:str='')->None:
    """处理加好友"""
    url = HTTP_URL+"/set_friend_add_request"
    params = {
        "flag": flag,
        "approve": approve,
        "remark": remark,
    }
    requests.get(url, params=params)
    
def get_group_file_system_info(group_id: int)->dict:
    """获取群文件系统信息
    @group_id: 群号
    @return: {
        'file_count': 文件总数 int32
        'limit_count': 文件上限 int32
        'used_space': 已使用空间 int64
        'total_space': 空间上限 int64
    }
    参考链接： https://docs.go-cqhttp.org/api/#%E8%8E%B7%E5%8F%96%E7%BE%A4%E6%96%87%E4%BB%B6%E7%B3%BB%E7%BB%9F%E4%BF%A1%E6%81%AF
    """
    url = HTTP_URL+"/get_group_file_system_info"
    params = {
        "group_id": group_id,
    }
    try:
        info = requests.get(url, params=params).json()
        if info['retcode'] != 0:
            warning("get_group_file_system_info requests not return ok")
            return {}
        return info['data']
    except requests.JSONDecodeError as e:
        warning("json decode error in get_group_file_system_info: {}".format(e))
    except BaseException as e:
        warning("base exception in get_group_file_system_info: {}".format(e))
    return {}

def get_group_root_files(group_id: int)->dict:
    """获取群根目录文件列表
    @group_id: 群号
    @return: {
        files: [] or None,
        folders: [] or None
    }
    参考链接: https://docs.go-cqhttp.org/api/#%E8%8E%B7%E5%8F%96%E7%BE%A4%E6%A0%B9%E7%9B%AE%E5%BD%95%E6%96%87%E4%BB%B6%E5%88%97%E8%A1%A8
    """
    url = HTTP_URL+"/get_group_root_files"
    params = {
        "group_id": group_id,
    }
    try:
        info = requests.get(url, params=params).json()
        if info['retcode'] != 0:
            warning("get_group_root_files requests not return ok")
            return {}
        return info['data']
    except requests.JSONDecodeError as e:
        warning("json decode error in get_group_file_system_info: {}".format(e))
    except BaseException as e:
        warning("base exception in get_group_root_files: {}".format(e))
    return {}

def get_group_files_by_folder(group_id: int, folder_id: str)->dict:
    """获取群子目录文件列表
    @group_id: 群号
    @folder_id: 文件夹id
    @return: {
        files: [] or None,
        folders: [] or None
    }
    参考链接: https://docs.go-cqhttp.org/api/#%E8%8E%B7%E5%8F%96%E7%BE%A4%E5%AD%90%E7%9B%AE%E5%BD%95%E6%96%87%E4%BB%B6%E5%88%97%E8%A1%A8
    """
    url = HTTP_URL+"/get_group_files_by_folder"
    params = {
        "group_id": group_id,
    }
    try:
        info = requests.get(url, params=params).json()
        if info['retcode'] != 0:
            warning("get_group_files_by_folder requests not return ok")
            return {}
        return info['data']
    except requests.JSONDecodeError as e:
        warning("json decode error in get_group_files_by_folder: {}".format(e))
    except BaseException as e:
        warning("base exception in get_group_files_by_folder: {}".format(e))
    return {}

def get_group_member_info(group_id: int, user_id: int, no_cache: bool=False)->Union[dict, None]:
    """获取群成员信息
    @group_id: 群号
    @user_id: 群成员qq
    @no_cache: 是否不使用缓存（使用缓存可能更新不及时, 但响应更快）

    @return:
        None if error,
        {
            group_id,
            user_id,
            nickname,
            card,
            sex,
            age,
            area,
            join_time,
            last_sent_time,
            level,
            role,
            unfriendly,
            title,
            title_expire_time,
            card_changeable,
            shut_up_timestamp,
        } if ok
    参考链接： https://docs.go-cqhttp.org/api/#%E8%8E%B7%E5%8F%96%E7%BE%A4%E6%88%90%E5%91%98%E4%BF%A1%E6%81%AF
    """
    url = HTTP_URL+"/get_group_member_info"
    params = {
        "group_id": group_id,
        "user_id": user_id,
        "no_cache": no_cache,
    }
    try:
        info = requests.get(url, params=params).json()
        if info['retcode'] != 0:
            warning("get_group_member_info requests not return ok")
            return None
        return info['data']
    except requests.JSONDecodeError as e:
        warning("json decode error in get_group_member_info: {}".format(e))
    except BaseException as e:
        warning("base exception in get_group_member_info: {}".format(e))
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
    """获取群成员列表
    @group_id: 群号
    @no_cache: 是否不使用缓存（使用缓存可能更新不及时, 但响应更快）

    @return:
        see get_group_member_info
    参考链接： https://docs.go-cqhttp.org/api/#%E8%8E%B7%E5%8F%96%E7%BE%A4%E6%88%90%E5%91%98%E5%88%97%E8%A1%A8
    """
    url = HTTP_URL+"/get_group_member_list"
    params = {
        "group_id": group_id,
        "no_cache": no_cache,
    }
    try:
        info = requests.get(url, params=params).json()
        if info['retcode'] != 0:
            warning("get_group_member_list requests not return ok")
            return None
        return info['data']
    except requests.JSONDecodeError as e:
        warning("json decode error in get_group_member_list: {}".format(e))
    except BaseException as e:
        warning("base exception in get_group_member_list: {}".format(e))
    return None

def get_group_file_url(group_id: int, file_id: str, busid: int)-> Union[str, None]:
    """获取群文件资源链接
    @group_id: 群号
    @file_id: 文件id
    @busid: 文件类型
    参考链接： https://docs.go-cqhttp.org/api/#%E8%8E%B7%E5%8F%96%E7%BE%A4%E6%96%87%E4%BB%B6%E8%B5%84%E6%BA%90%E9%93%BE%E6%8E%A5
    """
    url = HTTP_URL+"/get_group_file_url"
    params = {
        "group_id": group_id,
        "file_id": file_id,
        "busid": busid,
    }
    try:
        info = requests.get(url, params=params).json()
        if info['retcode'] != 0:
            warning("get_group_file_url requests not return ok")
            return None
        return info['data']['url']
    except requests.JSONDecodeError as e:
        warning("json decode error in get_group_file_url: {}".format(e))
    except BaseException as e:
        warning("base exception in get_group_file_url: {}".format(e))
    return None

def upload_group_file(group_id:int, file:str, name:str, folder:str)->None:
    """上传群文件
    @group_id: 群号
    @file:     文件的本地位置（绝对路径）
    @name:     上传后的文件名
    @folder:   上传到的文件夹名称，根目录为空字符串
    参考链接：   https://docs.go-cqhttp.org/api/#%E4%B8%8A%E4%BC%A0%E7%BE%A4%E6%96%87%E4%BB%B6
    """
    url = HTTP_URL+"/upload_group_file"
    params = {
        "group_id": group_id,
        "file": file,
        "name": name,
        "folder": folder,
    }
    try:
        info = requests.get(url, params=params).json()
        if info['retcode'] != 0:
            warning("upload_group_file requests not return ok")
            return None
        return info['data']
    except requests.JSONDecodeError as e:
        warning("json decode error in get_group_file_url: {}".format(e))
    except BaseException as e:
        warning("base exception in get_group_file_url: {}".format(e))
    return None
    

def set_group_ban(group_id:int, user_id:int, duration:int)->None:
    """群组单人禁言
    @group_id: 群号
    @user_id:  用户QQ号
    @duration: 禁言时间，单位：秒
    参考链接： https://docs.go-cqhttp.org/api/#%E7%BE%A4%E7%BB%84%E5%8D%95%E4%BA%BA%E7%A6%81%E8%A8%80
    """
    url = HTTP_URL+"/set_group_ban"
    params = {
        "group_id": group_id,
        "user_id": user_id,
        "duration": duration,
    }
    try:
        requests.get(url, params=params)
    except BaseException as e:
        warning("base exception in set_group_ban: {}".format(e))

def get_group_system_msg()->Optional[Dict[str, List[Dict[str, Any]]]]:
    """获取群系统消息（加群信息、邀请加群信息）
    @return: Optional[{
        'invited_requests': [{'request_id'}, ...]
    }]
    参考链接： https://docs.go-cqhttp.org/api/#%E8%8E%B7%E5%8F%96%E7%BE%A4%E7%B3%BB%E7%BB%9F%E6%B6%88%E6%81%AF
    """
    url = HTTP_URL+"/get_group_system_msg"
    try:
        req = requests.get(url)
        if req.status_code != requests.codes.ok:
            warning('requests code!=200 in get_group_system_msg')
            return None
        req = req.json()
        if req['retcode'] != 0:
            warning('retcode != 0 in get_group_system_msg')
            return None
        return req['data']
    except requests.exceptions.JSONDecodeError as e:
        warning('json decode error in get_group_system_msg: {}'.format(e))
    except BaseException as e:
        warning('base exception in get_group_system_msg: {}'.format(e))
    return None

def set_group_add_request(flag: str, sub_type: str, approve: bool, reason: str="")->None:
    """处理加群请求/处理加群邀请
    @flag: 加群请求的 flag（需从上报的数据中获得）
    @sub_type: 'add' 或 'invite', 需要和上报消息中的 sub_type 字段相符
    @approve: 是否同意
    @reason: 拒绝理由，仅approve == False时生效
    参考链接： https://docs.go-cqhttp.org/api/#%E5%A4%84%E7%90%86%E5%8A%A0%E7%BE%A4%E8%AF%B7%E6%B1%82-%E9%82%80%E8%AF%B7
    """
    if sub_type not in ['add', 'invite']:
        warning('sub_type should either `add` or `invite`, but: {}'.format(sub_type))
        return
    url = HTTP_URL+"/set_group_add_request"
    params = {
        'flag': flag,
        'sub_type': sub_type,
        'approve': approve,
        'reason': reason,
    }
    try:
        requests.get(url, params=params)
    except BaseException as e:
        warning('base exception in set_group_add_request: {}'.format(e))

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
