import datetime
import re
from utils.basic_event import send, warning, gocqQuote
from utils.standard_plugin import StandardPlugin
import json

def makeResource(what:str):
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    return {
        "app": "com.tencent.miniapp","desc": "","view": "notification","ver": "0.0.0.1","prompt": "该群即将解散","meta": {
            "notification": {
                "appInfo": {
                    "appName": "腾讯官方通知","appType": 4,"appid": 2034149631,"iconUrl": "https://q.qlogo.cn/headimg_dl?dst_uin=D00D2B5BF35B8B79453E11B5CAD17370&spec=100"
                },"data":[{
                    "title": "通知内容","value": "本群因%s，将于15分钟后解散，请自行遵守相关规定。\n\n\n腾讯科技\n%s"%(what, tomorrow.strftime('%Y年%m月%d日'))
                }],"emphasis_keyword": ""
            }
        }
    }
class MakeJoke(StandardPlugin):
    def __init__(self):
        self.pattern = re.compile(r'^\-joke\s*(.*)$')
    def judgeTrigger(self, msg, data):
        return self.pattern.match(msg) != None
    def executeEvent(self, msg, data):
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        jokeWhat = self.pattern.findall(msg)[0]
        if jokeWhat == '':
            jokeWhat = '你太美'
        send(target, '[CQ:json,data=%s]'%gocqQuote(json.dumps(makeResource(jokeWhat))), data['message_type'])
        return 'OK'
    def getPluginInfo(self, )->dict:
        return {
            'name': 'MakeJoke',
            'description': '开玩笑',
            'commandDescription': '-joke [...]',
            'usePlace': ['group', 'private'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }