import json
import random
import re
from typing import Any, List, Union

from utils.basicConfigs import ROOT_PATH
from utils.basicEvent import send
from utils.responseImage_beta import *
from utils.standardPlugin import StandardPlugin


class ThreeKingdomsRandom(StandardPlugin):
    def __init__(self) -> None:
        # self.flowers = ['红桃', '黑桃', '梅花', '方片']
        self.flowers = ['♥', '♠', '♣', '♦']
        self.points = [ 'A', '2', '3', '4', '5',
                        '6', '7', '8', '9', '10',
                        'J', 'Q', 'K']
    def judgeTrigger(self, msg: str, data) -> bool:
        return msg.startswith('判定')
    def executeEvent(self, msg: str, data) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        result = random.choice(self.flowers) + random.choice(self.points)
        send(target,'[CQ:reply,id=%d]你的判定结果是【%s】'%(data['message_id'], result), data['message_type'])
        return "OK"
    def getPluginInfo(self):
        return {
            'name': 'ThreeKingdomsRandom',
            'description': '三国杀判定',
            'commandDescription': '判定[...]?',
            'usePlace': ['group', 'private'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }

class RandomNum(StandardPlugin):
    def __init__(self) -> None:
        self.pattern = re.compile(r'^(\-?\d+)d(\-?\d+)$')
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return self.pattern.match(msg) != None
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        times, maxNum = self.pattern.findall(msg)[0]
        times = int(times)
        maxNum = int(maxNum)
        if times > 20:
            result = '对不起，我只有20个骰子~'
        elif times <= 0:
            result = '投掷次数要为正哦~'
        elif maxNum <= 0:
            result = '骰子最大点数必须是正数哦~'
        elif maxNum > 120:
            result = '对不起，我只能制作最多120个面的骰子~'
        else:
            result = ', '.join([str(random.randint(1, maxNum)) for _ in range(times)])
        send(target,'[CQ:reply,id=%d]%s'%(data['message_id'], result), data['message_type'])
        return 'OK'
    def getPluginInfo(self):
        return {
            'name': 'RandomNum',
            'description': '随机数生成',
            'commandDescription': '[骰子个数]d[骰子面数]',
            'usePlace': ['group', 'private'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
