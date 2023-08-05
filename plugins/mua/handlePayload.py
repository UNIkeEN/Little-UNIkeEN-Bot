from .client import Client 
import asyncio
import threading
from utils.standardPlugin import NotPublishedException
from utils.basicEvent import send, warning, gocqQuote
from utils.configAPI import getPluginEnabledGroups
from utils.responseImage_beta import *
from .common.subprotocols import Announcement, CreateAnnouncementPacket
import uuid
from utils.basicConfigs import sqlConfig, ROOT_PATH, SAVE_TMP_PATH
import mysql.connector
from typing import Any, Optional, Dict, List, Tuple
from icecream import ic
import time, datetime
from .annImgBed import urlOrBase64ToImage
from .clientInstance import muaClientInstance, loadMuaSession
from .annContextManager import recordAidWhenSucc
import os

def drawMuaListPic(savePath:str, muaList:Dict[str,List[Dict[str, Any]]])->Tuple[bool, str]:
    try:
        muaPic = ResponseImage(
            title = 'MUA 通知', 
            titleColor = PALETTE_CYAN,
            width = 1000,
            layout = 'normal',
            footer=datetime.datetime.now().strftime("更新时间： %Y-%m-%d %H:%M"),
            cardBodyFont= ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 24),
        )
        for channel, announcements in muaList.items():
            for announcement in announcements:
                is_new = False
                metadata = announcement.get('meta', None)
                if metadata != None and metadata.get('is_new', False):
                    is_new = True
                raw_content = []
                raw_content.append(('title', '['+channel+'] '+announcement['title']))
                if announcement.get('tags', None) != None:
                    raw_content.append(('keyword', ', '.join(announcement['tags'])))
                time_created = datetime.datetime.fromtimestamp(announcement['time_created'])
                raw_content.append(('subtitle', time_created.strftime('发布于 %Y-%m-%d %H:%M:%S')))
                if announcement.get('time_expires', None) != None:
                    texp = datetime.datetime.fromtimestamp(announcement['time_expires'])
                    raw_content.append(('subtitle', texp.strftime('截止于 %Y-%m-%d %H:%M:%S')))
                else:
                    raw_content.append(('subtitle', '自发布后15日截止'))
                if announcement.get('content', None) != None:
                    raw_content.append(('separator', ))
                    content = announcement['content']
                    for content_type, content_data in content:
                        if content_type == 'text':
                            raw_content.append(('body', content_data))
                        elif content_type in ['imgurl', 'imgbase64']:
                            img = urlOrBase64ToImage(content_type, content_data)
                            if img != None:
                                raw_content.append(('illustration', img))
                            else:
                                raw_content.append(('body', '[图片失效]'))
                        else:
                            pass
                muaPic.addCard(ResponseImage.RichContentCard(
                    raw_content = raw_content,
                    titleFontColor=PALETTE_CYAN,
                    backColor=PALETTE_LIGHTRED if is_new else None
                ))
        muaPic.generateImage(savePath)
        return True, savePath
    except BaseException as e:
        return False, str(e)

def drawMuaBriefListPic(savePath:str, muaList:Dict[str,List[Dict[str, Any]]])->Tuple[bool, str]:
    try:
        muaPic = ResponseImage(
            title = 'MUA 通知摘要', 
            titleColor = PALETTE_CYAN,
            width = 1000,
            layout = 'normal',
            footer=datetime.datetime.now().strftime("更新时间： %Y-%m-%d %H:%M"),
            cardBodyFont= ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 24),
        )
        # 先画摘要
        for channel, announcements in muaList.items():
            raw_content = [('title', channel, PALETTE_BLUE),('separator', )]
            for announcement in announcements:
                is_new = False
                metadata = announcement.get('meta', None)
                if metadata != None and metadata.get('is_new', False):
                    is_new = True
                if is_new:
                    raw_content.append(('body', '[新] '+announcement['title'], PALETTE_RED))
                else:
                    raw_content.append(('body', announcement['title']))
            muaPic.addCard(ResponseImage.RichContentCard(
                raw_content = raw_content,
                titleFontColor=PALETTE_CYAN,
            ))
        # 再画is_new
        for channel, announcements in muaList.items():
            for announcement in announcements:
                metadata = announcement.get('meta', None)
                if metadata == None or not metadata.get('is_new', False):
                    continue
                raw_content = []
                raw_content.append(('title', '['+channel+'] '+announcement['title']))
                if announcement.get('tags', None) != None:
                    raw_content.append(('keyword', ', '.join(announcement['tags'])))
                time_created = datetime.datetime.fromtimestamp(announcement['time_created'])
                raw_content.append(('subtitle', time_created.strftime('发布于 %Y-%m-%d %H:%M:%S')))
                if announcement.get('time_expires', None) != None:
                    texp = datetime.datetime.fromtimestamp(announcement['time_expires'])
                    raw_content.append(('subtitle', texp.strftime('截止于 %Y-%m-%d %H:%M:%S')))
                else:
                    raw_content.append(('subtitle', '自发布后15日截止'))
                if announcement.get('content', None) != None:
                    raw_content.append(('separator', ))
                    content = announcement['content']
                    for content_type, content_data in content:
                        if content_type == 'text':
                            raw_content.append(('body', content_data))
                        elif content_type in ['imgurl', 'imgbase64']:
                            img = urlOrBase64ToImage(content_type, content_data)
                            if img != None:
                                raw_content.append(('illustration', img))
                            else:
                                raw_content.append(('body', '[图片失效]'))
                        else:
                            pass
                muaPic.addCard(ResponseImage.RichContentCard(
                    raw_content = raw_content,
                    titleFontColor=PALETTE_CYAN,
                    backColor=None
                ))
        muaPic.addCard(ResponseImage.RichContentCard(
            raw_content = [('body', '发送 -mca 查看详细通知，发送 -mcb 查看通知摘要')],
            titleFontColor=PALETTE_CYAN,
            backColor=None
        ))
        muaPic.generateImage(savePath)
        return True, savePath
    except BaseException as e:
        return False, str(e)

def handle_payload_fn(session_id, payload):
    def quote(txt:str):
        return txt.replace('[', '&#91;').replace(']', '&#93;')
    data = loadMuaSession(session_id)
    body = payload.get_json_body()
    retType = payload.get_subprotocol_packet_type()
    ic(body)
    if data != None:
        # 单点通知
        if retType == 'RESULT':
            succ = body['success']
            reason = body['reason']
            send(data['target'], f'[CQ:reply,id={data["message_id"]}]succ: {succ}, reason: {reason}', data['message_type'])
            if succ:
                aid = body['aid']
                recordAidWhenSucc(aid, data)
        elif retType == 'LIST':
            savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'mualist_%d.png'%data['user_id'])
            if data['abstract']:
                succ, result = drawMuaBriefListPic(savePath, body)
            else:
                succ, result = drawMuaListPic(savePath, body)
            if succ:
                send(data['target'], f'[CQ:image,file=files:///{savePath}]', data['message_type'])
            else:
                warning(f'mua图片绘制失败: {result}')
    elif session_id == None:
        # 全服广播
        # TODO: 根据targets选择广播对象
        if retType == 'LIST':
            savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'mualist_global.png')
            succ, result = drawMuaBriefListPic(savePath, body)
            if succ:
                for groupId in getPluginEnabledGroups('muanotice'):
                    send(groupId, '检测到MUA通知更新：')
                    send(groupId, f'[CQ:image,file=files:///{savePath}]')
            else:
                warning(f'mua图片绘制失败: {result}')

muaClientInstance.set_handle_payload_fn(handle_payload_fn)
