from datetime import datetime
from threading import Semaphore
from typing import Any, Dict, List, Set, Union

from resources.api.dektAPI_v2 import actIdToUrlParam, getAllActivities, getCustomValue
from utils.basicConfigs import *
from utils.basicEvent import send
from utils.configAPI import getPluginEnabledGroups
from utils.responseImage_beta import *
from utils.sqlUtils import newSqlSession
from utils.standardPlugin import CronStandardPlugin, StandardPlugin

BASE_URL = "https://activity.sjtu.edu.cn"

METHOD = {
    0: "",
    1: "线上报名（审核录取）",
    2: "线下报名",
    3: "线上报名（先到先得）",
    4: "无需报名",
    5: "线上报名（随机录取）",
    6: "跳转其他报名",
    7: "不显示报名方式",
}

# 第二课堂建库，轮询监控最新活动
def createDektSql():
    mydb, mycursor = newSqlSession()
    mycursor.execute("""
    create table if not exists `sjtuNewDekt` (
        `dekt_seq` bigint unsigned not null auto_increment,
        `act_id` bigint unsigned not null,
        `update_time` timestamp default null,
        primary key (`dekt_seq`)
    )charset=utf8mb4, collate=utf8mb4_unicode_ci;""")
    
def appendDektActId(act_id:int):
    mydb, mycursor = newSqlSession()
    mycursor.execute("""
    insert into `sjtuNewDekt` (`act_id`, `update_time`) values (%s, %s)
    """, (str(act_id), datetime.now()))
    
def loadPrevActivities()->Set[str]:
    mydb, mycursor = newSqlSession(autocommit=False)
    mycursor.execute("""
    select `act_id` from `sjtuNewDekt`
    """)
    result = set()
    for id, in list(mycursor):
        result.add(id)
    return result
    
class SjtuDektMonitor(StandardPlugin, CronStandardPlugin):
    monitorSemaphore = Semaphore()
    def __init__(self, JAC_COOKIE:str, client_id:str) -> None:
        self.JAC_COOKIE = JAC_COOKIE
        self.client_id = client_id
        if SjtuDektMonitor.monitorSemaphore.acquire(blocking=False):
            self.start(20, 180)
            createDektSql()
        self.act_ids = []
        self.act_ids = list(loadPrevActivities())
        
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return False
    
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        return "OK"
    
    def tick(self, ):
        updateFlag = False
        activity_list = getAllActivities(self.JAC_COOKIE, self.client_id, 2, 1, 6)
        boardcastText = "✨第二课堂活动已更新："
        for record in activity_list:
            if record['id'] in self.act_ids: continue
            self.act_ids.append(record['id'])
            appendDektActId(record['id'])
            url = BASE_URL + "/activity/detail/" + actIdToUrlParam(record['id'])
            name = record['name']
            boardcastText += f"\n【{name}】{url}"
            updateFlag = True
        if updateFlag:
            customValues = [getCustomValue(self.JAC_COOKIE, self.client_id, a['id']) for a in activity_list]
            save_path = drawDektImg(activity_list, customValues)
            if save_path != None:
                for group_id in getPluginEnabledGroups('dektmonitor'):
                    send(group_id, boardcastText)
                    save_path = save_path if os.path.isabs(save_path) else os.path.join(ROOT_PATH, save_path)
                    send(group_id, '[CQ:image,file=file:///%s]'%save_path)
    def getPluginInfo(self, )->Any:
        return {
            'name': 'SjtuDektMonitor',
            'description': '第二课堂活动更新广播',
            'commandDescription': '[-grpcfg驱动]',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '2.0.0',
            'author': 'Unicorn',
        }

# 第二课堂与交大之声（讲座，API中活动类型为1），单次查询
class SjtuActivity(StandardPlugin): 
    def __init__(self, JAC_COOKIE:str, client_id:str):
        self.JAC_COOKIE = JAC_COOKIE
        self.client_id = client_id
        
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg in ['-dekt', '-jdzs']
    
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        if msg == '-dekt':
            activity_list = getAllActivities(self.JAC_COOKIE, self.client_id, 2, 1, 6)
            customValues = [getCustomValue(self.JAC_COOKIE, self.client_id, a['id']) for a in activity_list]
            save_path = drawDektImg(activity_list, customValues)
        else:
            speech_list = getAllActivities(self.JAC_COOKIE, self.client_id, 1, 1, 6)
            save_path = drawJdzsImg(speech_list)
        if save_path == None:
            send(target, '[CQ:reply,id=%d]生成失败'%data['message_id'], data['message_type'])
        else:
            save_path = save_path if os.path.isabs(save_path) else os.path.join(ROOT_PATH, save_path)
            send(target, '[CQ:image,file=file:///%s]'%save_path, data['message_type'])
        return "OK"
    
    def getPluginInfo(self, )->Dict[str, Any]:
        return {
            'name': 'SjtuDekt',
            'description': '交大活动',
            'commandDescription': '-dekt/-jdzs',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '2.0.0',
            'author': 'Unicorn',
        }
    
    def checkSelfStatus(self):
        if getAllActivities(self.JAC_COOKIE, self.client_id, 1, 1, 6) == None or\
           getAllActivities(self.JAC_COOKIE, self.client_id, 2, 1, 6) == None:
            return 1, 0, "获取第二课堂信息失败"
        return 1, 1, "正常"
        
def drawDektImg(data: List, customValues: List[Dict[str, str]]) -> Union[None, str]:
    DektCards = ResponseImage(
        titleColor=PALETTE_SJTU_ORANGE,
        title='第二课堂·最新活动',
        footer='数据更新于：'+datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S'),
        layout='normal',
        width=880,
        cardTitleFont=ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 27),
        cardBodyFont=ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 22),
    )
    
    for record, custom in zip(data, customValues):
        raw_content = [
            ('title', record['name']),
            ('body', record['sponsor']),
            ('separator',),
            ('body', f"{METHOD.get(record['method'], '')}" + (f" · {record['signed_up_num']} / {record['person_num']} 人" if record['person_num'] != None else ""), PALETTE_SJTU_ORANGE),
            ('body', f"活动时间：{record['activity_time'][0]} ~ {record['activity_time'][1]}")
        ]

        if record['registration_time'][0] and record['registration_time'][1]:
            raw_content.insert(-1, ('body', f"报名时间：{record['registration_time'][0]} ~ {record['registration_time'][1]}"))
        
        for k, v in custom.items():
            raw_content.append(('body', f'{k}： {v}'))
        
        DektCards.addCard(
            ResponseImage.RichContentCard(
                icon=BASE_URL + record['img'],
                raw_content=raw_content
            )
        )
        
    save_path = os.path.join(SAVE_TMP_PATH, 'dekt_newest.png')
    DektCards.generateImage(save_path)
    
    return save_path

def drawJdzsImg(data: List) -> Union[None, str]:
    JdzsCards = ResponseImage(
        titleColor=PALETTE_SJTU_DARKBLUE,
        title='交大之声·最新讲座',
        footer='数据更新于：'+datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S'),
        layout='normal',
        width=880,
        cardTitleFont=ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 27),
        cardBodyFont=ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 22),
    )
    
    for record in data:
        raw_content = [
            ('title', record['name']),
            ('body', record['sponsor']),
            ('separator',),
            ('body', f"{METHOD.get(record['method'], '')}", PALETTE_SJTU_DARKBLUE),
            ('body', f"{record['presenter']}"),
            ('body', f"{record['address']}"),
            ('body', f"{record['activity_time'][0]} ~ {record['activity_time'][1]}")
        ]

        JdzsCards.addCard(
            ResponseImage.RichContentCard(
                icon=BASE_URL + record['img'],
                raw_content=raw_content
            )
        )
        
    save_path = os.path.join(SAVE_TMP_PATH, 'jdzs_newest.png')
    JdzsCards.generateImage(save_path)
    
    return save_path
