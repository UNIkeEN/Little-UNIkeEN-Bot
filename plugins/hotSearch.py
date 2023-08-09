import requests
from datetime import datetime
from typing import Union, Any, Optional, Dict, List
from utils.basicEvent import *
from utils.basicConfigs import *
from utils.standardPlugin import StandardPlugin
from utils.hotSearchImage import HotSearchImage, Colors, Fonts
from utils.responseImage_beta import ResponseImage

def plotHotSearch(meta:List[Dict[str, Any]], width:int, imgPath:str)->None:
    """
    @meta: List[
        {
            "text": str,
            "color": Union[None, Colors],
            "font": Union[None, Fonts],
        }
    ]
    @imgPath: path to save image
    """
    generator = HotSearchImage(meta, width, Colors.PALETTE_BLACK, Fonts.FONT_SYHT_M24, Colors.PALETTE_WHITE)
    img = generator.draw()
    img.save(imgPath)

def getWeiboHotSearch()->Optional[List[Dict[str, Any]]]:
    """
    return object like:
    List[{
        "topic_flag": 1,
        "is_new": 1,
        "star_word": 0,
        "star_name": [
            "鸟鸟",
            "李诞"
        ],
        "mid": "4865756758544195",
        "word_scheme": "#鸟鸟因为李诞人设崩塌#",
        "onboard_time": 1675584748,
        "subject_querys": "综艺|开工了新生活",
        "expand": 0,
        "realpos": 9,
        "num": 360671,
        "word": "鸟鸟因为李诞人设崩塌",
        "ad_info": "",
        "raw_hot": 360671,
        "emoticon": "",
        "category": "综艺",
        "flag": 1,
        "label_name": "新",
        "icon_desc": "新",
        "small_icon_desc": "新",
        "icon_desc_color": "#ff3852",
        "note": "鸟鸟因为李诞人设崩塌",
        "subject_label": "综艺",
        "small_icon_desc_color": "#ff3852",
        "fun_word": 1,
        "flag_desc": "综艺",
        "channel_type": "Entertainment",
        "rank": 8
    }]
    """
    try:
        req = requests.get('https://weibo.com/ajax/side/hotSearch')
        if req.status_code != requests.codes.ok:
            return None
        wb = req.json()
        if wb['ok'] != 1:
            warning('weibo hot search api error')
            return None
        return wb['data']['realtime']
    except KeyError as e:
        warning('weibo api key error: {}'.format(e))
    except requests.JSONDecodeError as e:
        warning('weibo api json decode error: {}'.format(e))
    return None

class WeiboHotSearch(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg in ['微博热搜','热搜','wbrs','-wbrs']
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        wbhs = getWeiboHotSearch()
        if wbhs == None:
            send(target, "[CQ:reply,id={}]微博热搜获取失败".format(data['message_id']), data['message_type'])
        else:
            # hsWord = '\n'.join(['【%d】%s'%(hs['rank'], hs['word']) for hs in wbhs])
            # send(target, hsWord, data['message_type'])
            meta = [{'text':hs['word']} for hs in wbhs]
            imgPath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'wbrs_%s_%d.png'%(data['message_type'], target))
            img = plotHotSearch(meta, 550, imgPath)
            send(target, f'[CQ:image,file=files:///{imgPath}]', data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'WeiboHotSearch',
            'description': '微博热搜',
            'commandDescription': '热搜/微博热搜/wbrs/-wbrs',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
def getBaiduHotSearch()->Optional[List[Dict[str, Any]]]:
    try:
        req = requests.get('https://api.1314.cool/getbaiduhot/')
        if req.status_code != requests.codes.ok:
            return None
        bd = req.json()
        return bd['data']
    except KeyError as e:
        warning('baidu api key error: {}'.format(e))
    except requests.JSONDecodeError as e:
        warning('baidu api json decode error: {}'.format(e))
    return None

class BaiduHotSearch(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg in ['百度热搜', 'bdrs', '-bdrs']
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        bdhs = getBaiduHotSearch()
        if bdhs == None:
            send(target, "[CQ:reply,id={}]百度热搜获取失败".format(data['message_id']), data['message_type'])
        else:
            # hsWord = '\n'.join(['【%d】%s'%(rank+1, hs['word']) for rank, hs in enumerate(bdhs)])
            # send(target, hsWord, data['message_type'])
            meta = [{'text':hs['word']} for hs in bdhs]
            imgPath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'bdrs_%s_%d.png'%(data['message_type'], target))
            img = plotHotSearch(meta, 550, imgPath)
            send(target, f'[CQ:image,file=files:///{imgPath}]', data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'BaiduHotSearch',
            'description': '百度热搜',
            'commandDescription': '百度热搜/bdrs/-bdrs',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
def getZhihuHotSearch()->Optional[List[Dict[str, Any]]]:
    try:
        req = requests.get('https://api.zhihu.com/topstory/hot-list')
        if req.status_code != requests.codes.ok:
            return None
        zh = req.json()
        return zh['data']
    except KeyError as e:
        warning('zhihu api key error: {}'.format(e))
    except requests.JSONDecodeError as e:
        warning('zhihu api json decode error: {}'.format(e))
    return None

class ZhihuHotSearch(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg in ['知乎热搜', 'zhrs', '-zhrs']
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        zhrs = getZhihuHotSearch()
        if zhrs == None:
            send(target, "[CQ:reply,id={}]知乎热搜获取失败".format(data['message_id']), data['message_type'])
        else:
            a = ResponseImage(
                title='知乎热搜', 
                titleColor=Colors.PALETTE_SJTU_RED, 
                primaryColor=Colors.PALETTE_SJTU_RED, 
                footer='update at %s'%datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M"),
                layout='normal'
            )
            for rank, hs in enumerate(zhrs[:10]):
                try:
                    icon:str = hs['children'][0]['thumbnail']
                    if not isinstance(icon, str) or not icon.startswith('http'):
                        icon = None
                except:
                    icon = None
                a.addCard({
                    'style': 'normal',
                    'title': hs['target']['title'],
                    'keyword': str(datetime.fromtimestamp(hs['target']['created'])),
                    'body': hs['target']['excerpt'],
                    'icon': icon,
                })
            imgPath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'zhrs_%s_%d.png'%(data['message_type'], target))
            a.generateImage(imgPath)
            send(target, f'[CQ:image,file=files:///{imgPath}]', data['message_type'])

            # hsWord = '\n'.join(['【%d】%s'%(rank, hs['target']['excerpt']) for rank, hs in enumerate(zhrs[:5])])
            # send(target, hsWord, data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'ZhihuHotSearch',
            'description': '知乎热搜',
            'commandDescription': '知乎热搜/zhrs/-zhrs',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }