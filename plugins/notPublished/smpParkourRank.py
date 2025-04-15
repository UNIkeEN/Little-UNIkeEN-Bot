import datetime
import json
import re

import requests

from utils.basicConfigs import *
from utils.basicEvent import send
from utils.responseImage_beta import *
from utils.standardPlugin import Any, StandardPlugin, Union

PARKOUR_DATA_API = 'https://mc.sjtu.cn/smp2_parkour.php?pass=ynkdress'
UUID_MAP_API = f'https://skin.mualliance.ltd/api/union/profile/mapped/byuuid/'

DEFAULT_COURSE_ID = 14

class SMPParkourRank(StandardPlugin):
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return re.match(r'^-smprank(\s+\S+)?$', msg) is not None

    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type'] == 'group' else data['user_id']

        course = re.sub(r'^-smprank\s*', '', msg).strip()
        parkour_data = get_parkour_data()
        if not parkour_data:
            send(target, "获取跑酷数据失败", data['message_type'])
            return "OK"

        if not course:
            course = str(DEFAULT_COURSE_ID)

        if course.lower() == 'ls':
            valid_courses = {t['courseId'] for t in parkour_data['time']}
            courses_list = "\n".join([f"{c['courseId']} - {c['name']}" for c in parkour_data['course'] if c['courseId'] in valid_courses])
            send(target, f"当前赛道列表:\n{courses_list}", data['message_type'])
            return "OK"

        if course not in [c['courseId'] for c in parkour_data['course']]:
            send(target, "无效的赛道ID", data['message_type'])
            return "OK"

        sorted_data = process_data(parkour_data['time'], course)
        save_path = draw_parkour_rank(parkour_data['course'], sorted_data[:12], course)

        if (len(sorted_data) == 0):
            send(target, "赛道无记录", data['message_type'])
            return "OK"
        
        if save_path == None:
            send(data['group_id'], '[CQ:reply,id=%d]生成失败'%data['message_id'], data['message_type'])
        else:
            save_path = save_path if os.path.isabs(save_path) else os.path.join(ROOT_PATH, save_path)
            send(target, '[CQ:image,file=file:///%s]'%save_path, data['message_type'])
        return "OK"

    def getPluginInfo(self) -> Any:
        return {
            'name': 'SMPParkourRank',
            'description': 'SMP赛道排行',
            'commandDescription': '-smprank ls/[赛道名称]',
            'usePlace': ['group', 'private'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'SJMC',
        }

def get_parkour_data():
    url = PARKOUR_DATA_API
    response = requests.get(url)
    if response.status_code == 200:
        return json.loads(response.text)['data']
    else:
        print(f"request error: {response.status_code}")
        return None

def process_data(player_data, course=None):
    course_scores = [item for item in player_data if item['courseId'] == course]
    # sorting by time
    course_scores.sort(key=lambda x: int(x['time']))
    return course_scores

def draw_parkour_rank(course_list, sorted_data, course):
    if course_list is None or sorted_data is None:
        return None
    course_name = next(c['name'] for c in course_list if c['courseId'] == course)
    card_content = []
    max_num = max(int(item['time']) for item in sorted_data) if sorted_data else 1
    for index, item in enumerate(sorted_data):
        nickname = get_player_name(item['playerId'])
        count = int(item['time'])
        time_str = f"{count // 3600000:02}:{(count // 60000) % 60:02}:{(count // 1000) % 60:02}:{count % 1000:03}"
        text = f"{index + 1}. {nickname} ⏱ {time_str}"
        if index < 3:
            card_content.append(('subtitle', text))
            card_content.append(('progressBar', count / max_num, PALETTE_ORANGE, PALETTE_LIGHTORANGE))
        else:
            card_content.append(('body', text))
            card_content.append(('progressBar', count / max_num, PALETTE_GREEN, PALETTE_LIGHTGREEN))

    RankCards = ResponseImage(
        titleColor=PALETTE_SJTU_BLUE,
        title='SMP 赛道排行',
        footer='数据可能存在分钟级延迟',
        layout='normal',
        width=880,
        cardSubtitleFont=ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 27),
        cardBodyFont=ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 24),
    )
    RankCards.addCardList([
        ResponseImage.RichContentCard(
            raw_content=[
                ('keyword', f'赛道 : {course_name}'),
                ('separator',),
                ('subtitle', '截至 : ' + datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S'))
            ],
        ),
        ResponseImage.RichContentCard(
            raw_content=card_content
        )
    ])
    save_path = os.path.join(SAVE_TMP_PATH, 'parkour_rank.png')
    RankCards.generateImage(save_path)
    return save_path

def get_player_name(uuid):
    url = UUID_MAP_API + uuid
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data.get('name', uuid)
    else:
        print(f"Failed to retrieve data for UUID {uuid}, request error code: {str(response.status_code)}")
        return "Unknown Player"