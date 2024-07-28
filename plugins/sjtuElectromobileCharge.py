import re, datetime, time
from typing import List, Dict, Any, Tuple, Optional, Union
from utils.basicEvent import warning, send
from utils.standardPlugin import StandardPlugin, CronStandardPlugin, NotPublishedException
from utils.sqlUtils import newSqlSession
from utils.basicConfigs import ROOT_PATH, SAVE_TMP_PATH
from utils.configAPI import getPluginEnabledGroups
from utils.responseImage_beta import *
try:
    from resources.api.sjtuElectromobileAPI import getCharge
except:
    raise NotPublishedException('sjtu electrmobile api not published')
from io import BytesIO
from PIL import Image
import aiohttp, asyncio

def aioGetImages(imgUrls:List[str])->Dict[str, Optional[Image.Image]]:
    async def getImage(url:str)->Tuple[str, Optional[Image.Image]]:
        async with aiohttp.request('GET', url) as req:
            try:
                content = await req.read()
                img = Image.open(BytesIO(content))
            except Exception as e:
                img = None
            return url, img
    loop = asyncio.new_event_loop()
    tasks = [loop.create_task(getImage(url)) for url in imgUrls]
    result = loop.run_until_complete(asyncio.wait(tasks))
    loop.close()
    result = [r.result() for r in result[0]]
    result = {k:v for k, v in result}
    return result

def drawCharge(chargeInfo:List[Dict[str, Any]], savePath:str)->bool:
    chargeCard = ResponseImage(
        titleColor = PALETTE_SJTU_BLUE,
        title = '交大电动车充电桩',
        layout = 'normal',
        width = 880,
        footer=datetime.datetime.now().strftime('更新于 %Y-%m-%d  %H:%M:%S'),
        cardBodyFont= ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 24),
        cardSubtitleFont= ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 30),
    )
    places:Dict[str, List[Dict[str, Any]]] = {}
    # classify by displayIcon
    for place in chargeInfo:
        displayIcon = place['displayIcon']
        if displayIcon in places.keys():
            places[displayIcon].append(place)
        else:
            places[displayIcon] = [place]
    # aio get icon
    iconUrls = list(places.keys())
    icons = aioGetImages(iconUrls)
    for iconUrl, place in places.items():
        icon:Optional[Image.Image] = icons[iconUrl]
        content = []
        for p in place:
            name = p['website_name']
            idleCount = p['idle']
            totalCount = p['count']
            damageCount = p['damage']
            isOnline = p['device_status'] == 'online'
            # if not isOnline:
            #     name = '【离线】' + name
            name += '  闲{}/共{}'.format(idleCount, totalCount)
            if idleCount != 0:
                content.append(('subtitle', name))
            else:
                content.append(('body', name))
        chargeCard.addCard(ResponseImage.RichContentCard(
            subtitleFontColor=PALETTE_BLACK,
            bodyFontColor=PALETTE_GREY_CONTENT,
            raw_content=content,
            icon = icon,
        ))
    chargeCard.generateImage(savePath)
    return True
    
class GetSjtuCharge(StandardPlugin):
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg in ['-ddc']
    def executeEvent(self, msg: str, data: Any) -> Optional[str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        send(target, '正在获取电动车充电信息...', data['message_type'])
        chargeInfo = getCharge()
        if chargeInfo == None:
            send(target, '电动车充电信息获取失败，请联系bot管理员', data['message_type'])
        else:
            savePath = os.path.join(ROOT_PATH,SAVE_TMP_PATH,'charge.png')
            succ = drawCharge(chargeInfo, savePath)
            if succ:
                send(target, '[CQ:image,file=file:///{}]'.format(savePath), data['message_type'])
            else:
                send(target, '电动车充电信息解析失败', data['message_type'])
        return 'OK'
    def getPluginInfo(self) -> dict:
        return {
            'name': 'GetSjtuCharge',
            'description': '获取交大电动车充电信息',
            'commandDescription': '-ddc',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }