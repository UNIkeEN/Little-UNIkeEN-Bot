from typing import Union, Any
import requests
from utils.basic_event import *
from utils.basic_configs import *
from utils.standard_plugin import StandardPlugin
import urllib.parse
class Show2cyPIC(StandardPlugin): 
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg == '来点图图'
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        req = requests.get(url='https://tenapi.cn/acg',params={'return': 'json'})
        if req.status_code != requests.codes.ok:
            warning("tenapi failed in Show2cyPIC")
            return "OK"
        try:
            pic_url = req.json()['imgurl']
        except requests.JSONDecodeError as e:
            warning("json decode error in Show2cyPIC: {}".format(e))
            return "OK"
        except KeyError as e:
            warning("key error in Show2cyPIC: {}".format(e))
            return "OK"
        send(target,'[CQ:image,file=' + pic_url + ']', data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'Show2cyPIC',
            'description': '发送二次元图片',
            'commandDescription': '来点图图',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
class ShowSePIC(StandardPlugin): 
    def __init__(self) -> None:
        print('注意，开启ShowSePIC插件有被腾讯封号的危险')
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return startswith_in(msg, ['来点涩涩'])
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        msg_split = msg.split()
        if len(msg_split)==0:
            tag=''
        else:
            tag=msg.replace('来点涩涩','',1)
            tag=tag.strip().split()
            tagText = ""
            for t in tag:
                tagText += urllib.parse.quote(t) + '|'
            tagText = tagText[:-1]
            try:
                req= requests.get(url=f"https://api.lolicon.app/setu/v2?tag={tagText}&r18=0&size=regular",params={'return': 'json'})
                if req.status_code != requests.codes.ok:
                    warning("lolicon API failed in ShowSePIC")
                    return "OK"
                pic_url = req.json()['data'][0]['urls']['regular']
                target = data['group_id'] if data['message_type']=='group' else data['user_id']
                send(target,'[CQ:image,file=' + pic_url + ',type=flash]',data['message_type'])
            except BaseException as e:
                warning('exception in show2cyPic, error: {}'.format(e))
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'ShowSePIC',
            'description': '来点涩涩',
            'commandDescription': '来点涩涩 [tag]',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }