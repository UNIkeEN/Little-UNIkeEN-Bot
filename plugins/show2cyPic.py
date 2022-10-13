from typing import Union, Any
import requests
from utils.basicEvent import *
from utils.basicConfigs import *
from utils.standardPlugin import StandardPlugin
import urllib.parse
class Show2cyPIC(StandardPlugin): 
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg == '来点图图'
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        pic_url = requests.get(url='https://tenapi.cn/acg',params={'return': 'json'}).json()['imgurl']
        send(target,'[CQ:image,file=' + pic_url + ']', data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'Show2cyPIC',
            'description': '来点图图',
            'commandDescription': '来点图图',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
class ShowSePIC(StandardPlugin): 
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
                pic_url = requests.get(url=f"https://api.lolicon.app/setu/v2?tag={tagText}&r18=0&size=regular",params={'return': 'json'}).json()['data'][0]['urls']['regular']
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