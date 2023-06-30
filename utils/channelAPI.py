import requests, requests.exceptions, json
from utils.basicConfigs import HTTP_URL, APPLY_GROUP_ID
from typing import Dict, List, Union, Tuple, Any, Optional
from utils.basicEvent import warning
from utils.basicConfigs import MAIN_GUILD

def get_guild_list()->Optional[List[Dict[str, Any]]]:
    """获取频道列表
    @return: [{
        'nickname': 昵称, (str)
        'tiny_id': 自身的ID, (str)
        'avatar_url': 头像链接, (str)
    }]
    参考链接： https://docs.go-cqhttp.org/api/guild.html#%E8%8E%B7%E5%8F%96%E9%A2%91%E9%81%93%E5%88%97%E8%A1%A8
    """
    url = HTTP_URL+'/get_guild_list'
    try:
        req = requests.get(url=url)
        req = req.json()
        if req['retcode'] != 0:
            warning('retcode!=0 in get_guild_list')
            return []
        return req['data']
    except BaseException as e:
        warning("error in get_guild_list: {}".format(e))
        return []

def get_guild_channel_list(guild_id:str, no_cache:bool)->List[Dict[str, Any]]:
    """获取子频道列表
    @guild_id: 频道ID
    @no_cache: 是否无视缓存

    @return: [{

    }]
    参考链接： https://docs.go-cqhttp.org/api/guild.html#%E8%8E%B7%E5%8F%96%E5%AD%90%E9%A2%91%E9%81%93%E5%88%97%E8%A1%A8
    """
    url = HTTP_URL + '/get_guild_channel_list'
    params = {
        'guild_id': guild_id,
        'no_cache': no_cache
    }
    try:
        req = requests.get(url=url, params=params)
        req = req.json()
        if req['retcode'] != 0:
            warning('retcode!=0 in get_guild_channel_list')
            return []
        return req['data']
    except BaseException as e:
        warning("error in get_guild_channel_list: {}".format(e))
        return []

def send_guild_channel_msg(guild_id:str, channel_id:str, message:str)->Optional[Dict[str, Any]]:
    """发送信息到子频道
    @guild_id: 频道ID
    @channel_id: 子频道ID
    @message: 待发送的消息
    
    @return: {
        'message_id': 消息ID
    }
    参考链接： https://docs.go-cqhttp.org/api/guild.html#%E5%8F%91%E9%80%81%E4%BF%A1%E6%81%AF%E5%88%B0%E5%AD%90%E9%A2%91%E9%81%93
    """
    url = HTTP_URL+'/send_guild_channel_msg'
    params = {
        'guild_id': guild_id,
        'channel_id': channel_id,
        'message': message
    }
    print(params)
    try:
        req = requests.get(url=url, params=params)
        req = req.json()
        if req['retcode'] != 0:
            warning('retcode!=0 in send_guild_channel_msg')
            return None
        return req['data']
    except BaseException as e:
        warning("error in send_guild_channel_msg: {}".format(e))
        return None

def get_guild_meta_by_guest(guild_id:str)->Optional[Dict[str,Any]]:
    """通过访客获取频道元数据
    @guild_id: 频道ID

    @return: {
        'guild_id': 频道ID, (str)
        'guild_name': 频道名称, (str)
        'guild_profile': 频道简介, (str)
        'create_time': 创建时间, (int)
        ....
    }
    参考链接： https://docs.go-cqhttp.org/api/guild.html#%E9%80%9A%E8%BF%87%E8%AE%BF%E5%AE%A2%E8%8E%B7%E5%8F%96%E9%A2%91%E9%81%93%E5%85%83%E6%95%B0%E6%8D%AE
    """
    url = HTTP_URL+'/get_guild_meta_by_guest'
    params = {
        'guild_id': guild_id
    }
    try:
        req = requests.get(url=url, params=params)
        req = req.json()
        if req['retcode'] != 0:
            warning('retcode!=0 in get_guild_meta_by_guest')
            return None
        return req['data']
    except BaseException as e:
        warning("error in get_guild_meta_by_guest: {}".format(e))
        return None

def get_guild_member_list(guild_id:str, next_token:Optional[str]=None)->Dict[str, Any]:
    """获取频道成员列表
    @guild_id: 频道ID
    @next_token: 翻页token，为空的情况下, 将返回第一页的数据, 并在返回值附带下一页的 token

    @return: {
        'members': 成员列表, (List[GuildMemberInfo])
        'finished': 是否最终页, (bool)
        'next_token': 翻页token, (str)
    }
    参考链接： https://docs.go-cqhttp.org/api/guild.html#%E8%8E%B7%E5%8F%96%E9%A2%91%E9%81%93%E6%88%90%E5%91%98%E5%88%97%E8%A1%A8
    """
    url = HTTP_URL+'/get_guild_member_list'
    params = {
        'guild_id': guild_id
    }
    if next_token != None:
        params['next_token'] = next_token
    try:
        req = requests.get(url=url, params=params)
        req = req.json()
        if req['retcode'] != 0:
            warning('retcode!=0 in get_guild_member_list')
            return None
        return req['data']
    except BaseException as e:
        warning("error in get_guild_member_list: {}".format(e))
        return None