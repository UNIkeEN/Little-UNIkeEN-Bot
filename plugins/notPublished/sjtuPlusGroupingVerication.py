from utils.standardPlugin import StandardPlugin, AddGroupStandardPlugin, NotPublishedException
from utils.basicEvent import send, warning, set_group_add_request
from typing import Any, Union, List, Dict, Tuple, Optional
import requests, requests.exceptions
import re
try:
    from resources.api.sjtuPlusKey import SJTU_PLUS_GROUP_VERIFY_KEYS
except ImportError:
    raise NotPublishedException("sjtu plus key is secret")
    
class SjtuPlusGroupingVerify(AddGroupStandardPlugin):
    @staticmethod
    def commentToCode(comment:str)->str:
        code = comment.split('\n', maxsplit=1)[-1].split('：', maxsplit=1)[-1]
        return code

    def __init__(self, apiKeyName:str, appliedGroups:List[int]) -> None:
        self.apiKeyName = apiKeyName
        self.appliedGroups = appliedGroups
        self.apiKey = SJTU_PLUS_GROUP_VERIFY_KEYS[apiKeyName]
        self.triggerPattern = re.compile(r'^\s*([a-zA-Z0-9]{20,50})\s*')
        assert isinstance(self.apiKey, str)
        assert isinstance(self.appliedGroups, list) and all([isinstance(x, int) for x in self.appliedGroups])

    def judgeTrigger(self, data: Any) -> bool:
        return (data['group_id'] in self.appliedGroups and
            self.triggerPattern.match(self.commentToCode(data['comment'])) != None)
    
    def addGroupVerication(self, data: Any) -> Union[str, None]:
        vcode = self.triggerPattern.findall(self.commentToCode(data['comment']))[0]
        if isinstance(vcode, tuple):
            vcode = vcode[0]
        result = self.verify(data['user_id'], vcode)
        if result != None:
            if result:
                set_group_add_request(data['flag'], data['sub_type'], True, '欢迎入群！')
            else:
                set_group_add_request(data['flag'], data['sub_type'], False, '请确认您复制了正确的sjtu plus验证码')
        return 'OK'
        
    def verify(self, qq_number: int, token: str)->Optional[bool]:
        data = {
            'qq_number': str(qq_number),
            'token': token,
        }
        headers = {
            'Api-Key': self.apiKey
        }
        req = requests.post('https://plus.sjtu.edu.cn/attest/verify', headers=headers, json=data)
        print(req.text)
        try:
            result = req.json()
            return result['success']
        except requests.exceptions.JSONDecodeError as e:
            warning('json decode error in SjtuPlusGroupingVerify: {}'.format(e))
        except BaseException as e:
            warning('base exception in SjtuPlusGroupingVerify: {}'.format(e))
        return None