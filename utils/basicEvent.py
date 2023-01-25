import re
import mysql.connector
import requests, json
from utils.basicConfigs import HTTP_URL
from PIL import Image, ImageDraw, ImageFont
from utils.basicConfigs import *
import time
import random
from typing import Dict, List, Union, Tuple, Any
from pymysql.converters import escape_string
import traceback
import aiohttp, asyncio
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
    elif type=='private':
        params = {
            "message_type": type,
            "user_id": id,
            "message": message
        }
    print(params)
    # ###
    # pic=(re.findall("files://(.*?)]",message))
    # if len(pic)!=0:
    #     try:
    #         for f in pic:      
    #             img=Image.open(f)
    #             img.convert('L').save(f)
    #     except:
    #         pass
    # pic=(re.findall("files://(.*?),",message))
    # if len(pic)!=0:
    #     try:
    #         for f in pic:      
    #             img=Image.open(f)
    #             img.convert('L').save(f)
    #     except:
    #         pass
    # ###
    requests.get(url, params=params)
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
def set_friend_add_request(flag, approve=True)->None:
    """处理加好友"""
    url = HTTP_URL+"/set_friend_add_request"
    params = {
        "flag": flag,
        "approve": approve
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
    }
    try:
        info = requests.get(url, params=params).json()
        if info['retcode'] != 0:
            warning("get_group_file_url requests not return ok")
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

def warning(what:str)->None:
    """warning to admins"""
    stack = traceback.format_exc()
    what = '[warning]\n' + what 
    what += '\n\n[location]\n' + stack
    admin_users = ROOT_ADMIN_ID
    admin_groups = []
    # print(what)
    for admin in admin_users:
        send(admin, what, 'private')
    for admin in admin_groups:
        send(admin, what, 'group')

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
    timeNow = str(time.time()).replace('.', '-')
    speaker = random.choice(['枫原万叶', '可莉', '钟离',  '雷电将军',  '甘雨', '八重神子', '宵宫',  '胡桃'])
    num='1234567890'
    zw_num = '一二三四五六七八九十'
    for i in range(len(num)):
        sentence = sentence.replace(num[i],zw_num[i])
    response = requests.get(f"http://233366.proxy.nscc-gz.cn:8888/?text={sentence}&speaker={speaker}&length_factor=0.5&noise=0.4&format=mp3")
    if response.status_code != requests.codes.ok:
        raise RuntimeError("genshin voice api failed")
    file_path = "data/voice/{}.mp3".format(timeNow)
    with open(file_path, "wb") as code:
        code.write(response.content)
    return file_path

# config 相关
# see: https://dev.mysql.com/doc/refman/5.7/en/json-modification-functions.html
# globalConfig开表语句示例
# create table `BOT_DATA`.`globalConfig` (`groupId` bigint not null, `groupConfig` json, `groupAdmins` json, primary key (`groupId`));
# insert into `globalConfig` values (1234, '{"test1": {"name": "ftc", "enable": false}, "test2": {"name": "syj", "enable": true}}', '[]');
# insert into `globalConfig` values (8888, '{"test1": {"name": "ftc", "enable": true}, "test2": {"name": "syj", "enable": false}}', '[]');
def createGlobalConfig():
    """创建global config的sql table"""
    mydb = mysql.connector.connect(**sqlConfig)
    mycursor = mydb.cursor()
    mydb.autocommit = True
    mycursor.execute("""
    create database if not exists `BOT_DATA`
    """)
    mycursor.execute("""
    create table if not exists `BOT_DATA`.`globalConfig` (
        `groupId` bigint not null,
        `groupConfig` json,
        `groupAdmins` json,
        primary key (`groupId`)
    );""")

def readGlobalConfig(groupId: Union[None, int], pluginName: str)->Union[dict, Any, None]:
    """读global config
    @groupId
        if None, then read add groups config
        elif int, read the specific group config
        else: warning
    @pluginName
        like 'test1.enable' or 'test1'
    """
    mydb = mysql.connector.connect(**sqlConfig)
    mycursor = mydb.cursor()
    pluginName = escape_string(pluginName)
    if groupId == None:
        result = {}
        try:
            mycursor.execute("SELECT groupId, json_extract(groupConfig,'$.%s') from BOT_DATA.globalConfig"%pluginName)
        except mysql.connector.Error as e:
            warning("error in readGlobalConfig: {}".format(e))
            return None
        for grpId, groupConfig in list(mycursor):
            if groupConfig != None:
                result[grpId] = json.loads(groupConfig)
        return result
    elif isinstance(groupId, int):
        result = {}
        try:
            mycursor.execute("SELECT groupId, json_extract(groupConfig, '$.%s') from BOT_DATA.globalConfig where groupId = %d"%(pluginName, groupId))
        except mysql.connector.Error as e:
            warning("error in readGlobalConfig: {}".format(e))
            return None
        for grpId, groupConfig in list(mycursor):
            if groupConfig != None:
                result[grpId] = json.loads(groupConfig)
        if len(result) == 0:
            return None
        else:
            return result[groupId]
    else:
        warning("unknow groupId type in readGlobalConfig: groupId = {}".format(groupId))
        return None
# update BOT_DATA.test set groupConfig=json_set(groupConfig, '$.test1.enable', False) where groupId=1234;
def writeGlobalConfig(groupId: Union[None, int], pluginName: str, value: Any):
    """写global config
    @groupId
        if None, then write all groups' config
        elif int, write the specific group config
        else: warning
    @pluginName
        like 'test1.enable' or 'test1'
    @value
    """
    mydb = mysql.connector.connect(**sqlConfig)
    mycursor = mydb.cursor()
    pluginName = escape_string(pluginName)
    if groupId == None:
        try:
            mycursor.execute("update BOT_DATA.globalConfig set groupConfig=json_set(groupConfig, '$.%s', cast('%s' as json))"%(pluginName, json.dumps(value)))
        except mysql.connector.Error as e:
            warning("error in writeGlobalConfig: {}".format(e))
    elif isinstance(groupId, int):
        try:
            mycursor.execute("insert ignore into BOT_DATA.globalConfig(groupId, groupConfig, groupAdmins) values (%d, '{}', '[]')"%groupId)
            mycursor.execute("update BOT_DATA.globalConfig set groupConfig=json_set(groupConfig, '$.%s', cast('%s' as json)) where groupId=%d"%(pluginName, json.dumps(value), groupId))
        except mysql.connector.Error as e:
            warning("mysql error in writeGlobalConfig: {}".format(e))
    else:
        warning("unknow groupId type in writeGlobalConfig: groupId = {}".format(groupId))
    mydb.commit()

def getPluginEnabledGroups(pluginName: str)->List[int]:
    """获取开启插件的群聊id列表
    @pluginName: 被pluginGroupManager管理的插件组名称
        eg: "faq", "superemoji"

    @return: 开启插件的群id列表
    """
    mydb = mysql.connector.connect(**sqlConfig)
    mycursor = mydb.cursor()
    pluginName = escape_string(pluginName)
    try:
        mycursor.execute("select groupId from BOT_DATA.globalConfig \
            where json_extract(groupConfig, '$.%s.enable') = true"%escape_string(pluginName))
        return [x[0] for x in list(mycursor)]
    except mysql.connector.Error as e:
        warning("mysql error in getPluginEnabledGroups: {}".format(e))

def getGroupAdmins(groupId: int)->List[int]:
    """获取群bot管理列表
    @groupId: 群号
    @return:  群bot管理员QQ号列表
    """
    mydb = mysql.connector.connect(**sqlConfig)
    mycursor = mydb.cursor()
    try:
        mycursor.execute("select groupAdmins from BOT_DATA.globalConfig where groupId = %s"%(groupId))
        result = list(mycursor)
        if len(result) <= 0:
            mycursor.execute("insert ignore into BOT_DATA.globalConfig(groupId, groupConfig, groupAdmins) values (%d, '{}', '[]')"%groupId)
            mydb.commit()
            return []
        else:
            result = json.loads(result[0][0])
            if not isinstance(result, list) or any([not isinstance(x, int) for x in result]):
                warning('error admin type, groupId = %d'%groupId)
                return []
            return result
    except mysql.connector.Error as e:
        warning("error in getGroupAdmins: {}".format(e))
        return []

def addGroupAdmin(groupId: int, adminId: int):
    """添加群bot管理
    @groupId: 群号
    @adminId: 新添加的群bot管理员QQ号
    """
    if not isinstance(groupId, int) or not isinstance(adminId, int):
        warning("error groupId type or adminId type in addGroupAdmin: groupId = {}, adminId = {}".format(groupId, adminId))
        return
    mydb = mysql.connector.connect(**sqlConfig)
    mycursor = mydb.cursor()
    try:
        mycursor.execute("insert ignore into BOT_DATA.globalConfig(groupId, groupConfig, groupAdmins) values (%d, '{}', '[]')"%groupId)
        mycursor.execute("update BOT_DATA.globalConfig set groupAdmins=json_array_append(groupAdmins,'$', %d) where groupId=%d;"%(adminId, groupId))
        mydb.commit()
    except mysql.connector.Error as e:
        warning("error in addGroupAdmin: {}".format(e))
def setGroupAdmin(groupId: int, adminIds: List[int]):
    """设置群bot管理为某个list
    @groupId: 群号
    @adminIds: 更改后的群bot管理员QQ号列表
    """
    if not isinstance(adminIds, list) or any([not isinstance(x, int) for x in adminIds]):
        warning('error admin type, groupId = %d'%groupId)
        return
    mydb = mysql.connector.connect(**sqlConfig)
    mycursor = mydb.cursor()
    try:
        mycursor.execute("insert ignore into BOT_DATA.globalConfig(groupId, groupConfig, groupAdmins) values (%d, '{}', '[]')"%groupId)
        mycursor.execute("update BOT_DATA.globalConfig set groupAdmins='%s' where groupId=%d;"%(json.dumps(adminIds), groupId))
        mydb.commit()
    except mysql.connector.Error as e:
        warning("error in setGroupAdmin: {}".format(e))
def delGroupAdmin(groupId: int, adminId: int):
    """删除群bot管理员
    @groupId: 群号
    @adminId: 要删除的群bot管理员QQ号
    """
    if not isinstance(groupId, int) or not isinstance(adminId, int):
        warning("error groupId type or adminId type in delGroupAdmin: groupId = {}, adminId = {}".format(groupId, adminId))
        return
    groupAdmins = getGroupAdmins(groupId)
    if groupAdmins == None:
        warning("groupAdmins is None at delGroupAdmin")
        return
    groupAdmins = set(groupAdmins)
    if adminId not in groupAdmins:
        warning("id = '%d' not in admins at delGroupAdmin"%adminId)
        return
    groupAdmins.remove(adminId)
    setGroupAdmin(groupId, list(groupAdmins))