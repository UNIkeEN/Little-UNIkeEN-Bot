from typing import Union, Any
from utils.basic_event import *
from utils.basic_configs import *
from utils.response_image import FONT_SYHT_M32
from utils.standard_plugin import StandardPlugin, NotPublishedException
from PIL import Image, ImageDraw, ImageFont
import os.path
from utils.response_image import *
import json
import random

EE0502_DATA_PATH = 'resources/corpus/izf.json'
try:
    with open(EE0502_DATA_PATH, 'r', encoding='utf-8') as f:
        json.load(f)['results']
except:
    raise NotPublishedException("izf.json is secret")


def draw_comment_ee0502(t):
    izf = ResponseImage(title='我爱电路实验',
                        primaryColor=PALETTE_CYAN,
                        layout='normal',
                        footer='数据来源：SJTU选课社区',
                        autoSize=True,
                        cardBodyFont=FONT_SYHT_M24,
                        width=880)
    izf.add_card(
        ResponseImage.NormalCard(
            title='# ' + str(t['id']),
            keyword='评分: ' + str(t['rating']) + ('     成绩: ' + str(t['score']) if t['score'] != None else ''),
            subtitle=t['modified'],
            body=t['comment']
        )
    )
    savePath = os.path.join(SAVE_TMP_PATH, "izf.png")
    izf.generate_image(savePath)
    return savePath


class ShowEE0502Comments(StandardPlugin):
    def __init__(self) -> None:
        with open(EE0502_DATA_PATH, 'r', encoding='utf-8') as f:
            zf_data = json.load(f)['results']
        self.resource = zf_data

    def judge_trigger(self, msg: str, data: Any) -> bool:
        return msg in ['ttzf', 'izf', '-ttzf', '-izf']

    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type'] == 'group' else data['user_id']
        t = random.choice(self.resource)
        picPath = draw_comment_ee0502(t)
        picPath = picPath if os.path.isabs(picPath) else os.path.join(ROOT_PATH, picPath)
        send(target, f'[CQ:image,file=files:///{picPath}]', data['message_type'])
        return "OK"

    def get_plugin_info(self, ) -> Any:
        return {
            'name': 'izf',
            'description': '我爱电路实验',
            'commandDescription': 'ttzf / izf',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.2',
            'author': 'Unicorn',
        }
