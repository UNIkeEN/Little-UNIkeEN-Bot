from utils.basicConfigs import sqlConfig
import mysql.connector
from utils.standardPlugin import CronStandardPlugin, StandardPlugin
import datetime
import asyncio
import aiohttp
from utils.basicEvent import warning, send
from typing import List, Dict, Tuple, Any, Optional, Union
import time
import re, os.path
from utils.basicConfigs import ROOT_PATH, SAVE_TMP_PATH, FONTS_PATH
from matplotlib import pyplot as plt
import matplotlib.dates as mdates
from matplotlib.font_manager import FontProperties 

font = FontProperties(fname=os.path.join(FONTS_PATH, 'SourceHanSansCN-Normal.otf'), size=14)

def createSjtuClassroomSql():
    mydb = mysql.connector.connect(charset='utf8mb4',**sqlConfig)
    mydb.autocommit = True
    mycursor = mydb.cursor()
    mycursor.execute("""
    create table if not exists `BOT_DATA`.`sjtuClassroomRecord` (
        `roomName` char(20) not null,
        `time` timestamp not null,
        `actualStuNum` int not null,
        primary key(`roomName`, `time`)
    )charset=utf8mb4, collate=utf8mb4_unicode_ci""")

def aioGetAllBuildingCourse(targetDate:datetime.date)->List[Dict]:
    payloads = [126, 128, 127, 122, 564, 124, 125]
    payloads = [targetDate.strftime(f'buildId={p}&courseDate=%Y-%m-%d') for p in payloads]
    url = 'https://ids.sjtu.edu.cn/build/findBuildRoomType'
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "close",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Host": "ids.sjtu.edu.cn",
        "Origin": "https://ids.sjtu.edu.cn",
        "Referer": "https://ids.sjtu.edu.cn/classroomUse/goPage?param=00f9e7d21b8915f2595bcf4c5e83d41e5fa0251ff700451747b9ebe10b033327",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        'sec-ch-ua': '"Not_A Brand";v="99", "Google Chrome";v="109", "Chromium";v="109"',
        "sec-ch-ua-mobile": "?0",
        'sec-ch-ua-platform': '"Windows"',
    }
    async def getCourse(payload:str)->Optional[Dict]:
        async with aiohttp.request('POST', url=url, headers=headers, data=payload) as req:
            try:
                result = await req.json()
                if result['code'] != 200:
                    return None
                return result['data']
            except BaseException as e:
                return None
    loop = asyncio.new_event_loop()
    tasks = [loop.create_task(getCourse(p)) for p in payloads]
    results = loop.run_until_complete(asyncio.wait(tasks))
    loop.close()
    results = [r.result() for r in results[0]]
    buildingInfos = [r for r in results if r != None]
    if len(buildingInfos) != len(results):
        warning('getCourse api failed in sjtuClassroomRecorder.aioGetAllBuildingCourse')
    return buildingInfos

def processBuildingCourse(targetDate:datetime.date)->Dict[str, int]:
    result = {}
    buildingInfos = aioGetAllBuildingCourse(targetDate)
    for buildingInfo in buildingInfos:
        roomStudents = {room['roomId']: int(room['actualStuNum']) for floor in buildingInfo['floorList'] for room in floor.get('roomStuNumbs', [])}            
        rooms = {room['name']: room for floor in buildingInfo['floorList'] for room in floor['children'] }
        for roomName, roomInfo in rooms.items():
            roomId = roomInfo['id']
            if roomId not in roomStudents.keys():
                continue
            numStudents = roomStudents[roomId]
            result[roomName] = numStudents
    return result

def recordSjtuClassroom(result:Dict[str, int], now: datetime.datetime):
    mydb = mysql.connector.connect(charset='utf8mb4',**sqlConfig)
    mydb.autocommit = True
    mycursor = mydb.cursor()
    timestamp = int(time.mktime(now.timetuple()))
    for roomName, actualStuNum in result.items():
        mycursor.execute("""
        insert into `BOT_DATA`.`sjtuClassroomRecord` (
            `roomName`, `actualStuNum`, `time`
        ) values (%s, %s, from_unixtime(%s))
        """,(roomName, actualStuNum, timestamp))
    
class SjtuClassroomRecorder(CronStandardPlugin):
    def __init__(self) -> None:
        createSjtuClassroomSql()
        self.start(0, 10*60)
    def tick(self) -> None:
        now = datetime.datetime.now()
        today = now.date()
        recordSjtuClassroom(processBuildingCourse(today), now)

def standarlizingRoomStr(roomStr:str)->Optional[Tuple[str, str]]:
    """
    东上103 => (东上院, 东上院103)
    东中1-105 => (东中院, 东中院1-105)
    陈瑞球103 => (陈瑞球楼, 陈瑞球楼103)
    你好 => None
    """
    pattern1 = re.compile(r'^(上|中|下|东上|东下)院?\s*(\d{3})$')
    if pattern1.match(roomStr) != None:
        building, roomCode = pattern1.findall(roomStr)[0]
        building += '院'
        return building, building + roomCode
    pattern2 = re.compile(r'^东中(院?\s*)(\d\-\d{3})$')
    if pattern2.match(roomStr) != None:
        building = '东中院'
        _, roomCode = pattern2.findall(roomStr)[0]
        return building, building+roomCode
    pattern3 = re.compile(r'^(陈瑞球楼?|球楼?)\s*(\d{3})$')
    if pattern3.match(roomStr) != None:
        building = '陈瑞球楼'
        _, roomCode = pattern3.findall(roomStr)[0]
        return building, building + roomCode
    return None
def getWeekDay(targetDate:datetime.date)->str:
    return '星期' + ['一','二','三','四','五','六','日'][targetDate.weekday()]
def drawClassroomPeopleCountFunc(roomName:str, target:int)->Tuple[bool, str]:
    mydb = mysql.connector.connect(charset='utf8mb4',**sqlConfig)
    mydb.autocommit = True
    mycursor = mydb.cursor()
    now = datetime.datetime.now()
    today = now.date()
    mycursor.execute("""select time, actualStuNum from `BOT_DATA`.`sjtuClassroomRecord` where
    roomName = %s and TIMESTAMPDIFF(DAY, time, %s) < 5 order by time desc;""", (roomName, today))
    result = list(mycursor)
    if len(result) < 30:
        return False, '没有该教室的信息'
    xList = [[] for _ in range(5)]
    yList = [[] for _ in range(5)]
    for t, c in result:
        dt = (today - t.date()).days
        if dt>=5:
            break
        xList[dt].append(t.replace(2000, 1, 1))
        yList[dt].append(c)
    # timeList, peopleCount = zip(*result)
    plt.figure(figsize=(10, 3))
    for i in range(5):
        tDate = today - datetime.timedelta(days=i)
        weekday = getWeekDay(tDate)
        plt.plot(xList[i], yList[i], label=tDate.strftime(f"%Y-%m-%d {weekday}"))
    plt.legend(loc='upper left', prop=font)
    plt.xticks(rotation=25,size=9)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))  
    savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'classroomPeopleCount-%d.png'%target)
    plt.savefig(savePath, dpi=400, bbox_inches='tight', pad_inches=0 )
    plt.close()
    return True, savePath

class DrawClassroomPeopleCount(StandardPlugin):
    def __init__(self):
        self.triggerPattern = re.compile(r'^(\-jsrsls|教室人数历史)\s+(\S*)$')
    def judgeTrigger(self, msg:str, data:Any)->bool:
        return self.triggerPattern.match(msg) != None
    def executeEvent(self, msg:str, data:Any)->Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        _, roomStr = self.triggerPattern.findall(msg)[0]
        result = standarlizingRoomStr(roomStr)
        if result == None:
            send(target, '教室参数解析错误，请重新输入查询参数，例如：\n"-jsrsls 东上105"、"教室人数历史 东下院311"、"-jsrsls 东中1-102"', data['message_type'])
            return "OK"
        _, roomName = result
        succ, result = drawClassroomPeopleCountFunc(roomName, target)
        if succ:
            send(target, '[CQ:image,file=file:///%s]'%result, data['message_type'])
        else:
            send(target, f'[CQ:reply,id={data["message_id"]}]查询结果错误，可能原因是：{result}', data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'DrawClassroomPeopleCount',
            'description': '教室人数历史',
            'commandDescription': '-jsrsls [东上院102/东中1-105/...]',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
