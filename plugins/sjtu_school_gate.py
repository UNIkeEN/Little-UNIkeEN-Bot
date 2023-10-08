from typing import Dict, Union, Any, List, Tuple, Optional
from utils.basic_event import send, warning
from utils.standard_plugin import StandardPlugin
from utils.basic_configs import ROOT_PATH, SAVE_TMP_PATH
import requests, datetime
from utils.response_image_beta import *

# canMv = {
#     0: '禁止机动车通行',
#     1: '允许机动车通行',
#     2: '仅限校内车辆'
# }
# nmvTrafficPeriod: 行人通行时间
# mvTrafficPeriod:  机动车通行时间
def getSchoolGateStatus()->Optional[List[Dict]]:
    url = "https://campuslife.sjtu.edu.cn/api/schoolGateTraffic"
    req = requests.get(url=url)
    if req.status_code != requests.codes.ok:
        return None
    try:
        result = req.json()
        if result['code'] != 0: return None
        return result['data']
    except:
        return None

def drawSchoolGatePic(gatesInfo:List[Dict], savePath:str)->Tuple[bool, str]:
    gateCard = ResponseImage(
        title = '交大校门', 
        titleColor = PALETTE_CYAN,
        width = 1000,
        layout = 'two-column',
        footer=datetime.datetime.now().strftime("更新时间： %Y-%m-%d %H:%M"),
        cardBodyFont= ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 24),
    )
    for gateInfo in gatesInfo:
        content = []
        if gateInfo['isOpen']:
            fatalColor = PALETTE_RED
            warningColor = PALETTE_ORANGE
            infoColor = PALETTE_BLACK
            content.append(('title', gateInfo['campus'] + ' - ' + gateInfo['gate'], infoColor))
        else:
            fatalColor = PALETTE_LIGHTRED
            warningColor = PALETTE_LIGHTORANGE
            infoColor = PALETTE_GREY_CONTENT
            content.append(('title', gateInfo['campus'] + ' - ' + gateInfo['gate']+'  [关闭]', infoColor))
        content.append(('subtitle', gateInfo['address'], infoColor))

        if gateInfo['canMv'] == 0:
            content.append(('subtitle', '禁止机动车通行', fatalColor))
        elif gateInfo['canMv'] == 2:
            content.append(('subtitle', '仅限校内车辆', warningColor))
        if gateInfo['note'] != None and len(gateInfo['note'])>0:
            content.append(('subtitle', gateInfo['note'], fatalColor))
        else:
            if gateInfo['mvTrafficPeriod'] != None:
                content.append(('body', '机动车通行时间： ' + gateInfo['mvTrafficPeriod'], infoColor))
            if gateInfo['nmvTrafficPeriod'] != None:
                content.append(('body', '行人通行时间： ' + gateInfo['nmvTrafficPeriod'], infoColor))
        gateCard.addCard(ResponseImage.RichContentCard(
            raw_content=content,
            titleFontColor=PALETTE_CYAN,
        ))
    gateCard.generateImage(savePath)
    return True, savePath

class SjtuSchoolGate(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg == '-gate'
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        gatesInfo = getSchoolGateStatus()
        if gatesInfo == None:
            send(target, '[CQ:reply,id=%d]API请求失败，请稍后重试'%data['message_id'], data['message_type'])
        else:
            savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'gate_%d.png'%target)
            succ, result = drawSchoolGatePic(gatesInfo, savePath)
            if succ:
                send(target, '[CQ:image,file=files:///%s]'%savePath, data['message_type'])
            else:
                send(target, '[CQ:reply,id=%d]数据绘制失败，请联系管理员'%data['message_id'], data['message_type'])
        return "OK"
    def getPluginInfo(self)->Any:
        return {
            'name': 'SjtuSchoolGate',
            'description': '交大校门',
            'commandDescription': '-gate',
            'usePlace': ['group', 'private'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }