import datetime
import os.path
import re
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from matplotlib import pyplot as plt
from PIL import Image, ImageDraw

from utils.basicConfigs import ROOT_PATH, SAVE_TMP_PATH
from utils.basicEvent import send, warning
from utils.hotSearchImage import Colors, Fonts, HotSearchImage
from utils.responseImage_beta import (FONT_SYHT_M28, PALETTE_GREEN,
                                      PALETTE_GREY_BORDER, PALETTE_SJTU_RED,
                                      ResponseImage, draw_rounded_rectangle)
from utils.standardPlugin import StandardPlugin

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

def getSjtuBuilding(building:str)->Optional[Any]:
    """获取教室信息（温度、湿度、人数、PM2.5等）
    @building: 教学楼[上院/中院/...]
    """
    url = 'https://ids.sjtu.edu.cn/classroomUse/findSchoolCourseInfo'
    
    datas = {
        '上院': 'buildId=126',
        '中院': 'buildId=128',
        '下院': 'buildId=127',
        '东上院': 'buildId=122',
        '东中院': 'buildId=564',
        '东下院': 'buildId=124',
        '陈瑞球楼': 'buildId=125',
        '新上院': 'buildId=663',
        '工程馆': 'buildId=697'
    }
    data = datas[building]
    # try:
    session = requests.session()
    session.get('https://ids.sjtu.edu.cn')
    session.get("https://jaccount.sjtu.edu.cn")
    req = session.post(url=url, headers=headers, data=data)
    session.close()
    # except BaseException as e:
    #     warning('base exception while requesting sjtu classroom: {}'.format(e))
    #     return None
    if req.status_code != requests.codes.ok:
        warning("sjtu classroom API failed!")
        return None
    try:
        result = req.json()
        if result['code'] != 200:
            warning("code != 200, sjtu classroom API failed in getSjtuBuilding")
            return None
        return result['data']
    except requests.JSONDecodeError as e:
        warning('json decode error while getting sjtu classroom: {}'.format(e))
    except BaseException as e:
        warning('base exception while getting sjtu classroom: {}'.format(e))
    return None

def getRoomCourse(building:str, targetDate:datetime.date)->Optional[Any]:
    url = 'https://ids.sjtu.edu.cn/build/findBuildRoomType'
    payload = {
        '上院': 'buildId=126',
        '中院': 'buildId=128',
        '下院': 'buildId=127',
        '东上院': 'buildId=122',
        '东中院': 'buildId=564',
        '东下院': 'buildId=124',
        '陈瑞球楼': 'buildId=125',
        '新上院': 'buildId=663',
        '工程馆': 'buildId=697'
    }[building] + targetDate.strftime('&courseDate=%Y-%m-%d')
    try:
        result = requests.post(url=url, headers=headers, data=payload).json()
        if result['code'] != 200:
            warning("code != 200, sjtu classroom API failed in getRoomCourse")
            return None
        return result['data']
    except BaseException as e:
        warning('base exception in getRoomCourse: {}'.format(e))
        return None

def getRoomDate()->Optional[Any]:
    url = 'https://ids.sjtu.edu.cn/course/findCurSemester'
    try:
        result = requests.post(url=url, headers=headers).json()
        if result['code'] != 200:
            warning("code != 200, sjtu classroom API failed in getRoomDate")
            return None
        return result['data']
    except BaseException as e:
        warning('base exception in getRoomDate: {}'.format(e))
        return None


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
        return building, building + roomCode
    pattern3 = re.compile(r'^(陈瑞球楼?|球楼?)\s*(\d{3})$')
    if pattern3.match(roomStr) != None:
        building = '陈瑞球楼'
        _, roomCode = pattern3.findall(roomStr)[0]
        return building, building + roomCode
    pattern4 = re.compile(r'^(工程?馆?)\s*(\d{3})$')
    if pattern4.match(roomStr) != None:
        building = '工程馆'
        _, roomCode = pattern4.findall(roomStr)[0]
        return building, building + roomCode
    pattern5 = re.compile(r'^(新上院?)\s*(N|S|n|s)(\d{3})([A-Za-z]?)$')
    if pattern5.match(roomStr) != None:
        building = '新上院'
        _, loc, roomCode, postfix = pattern5.findall(roomStr)[0]
        return building, building + loc.upper() + roomCode + postfix.upper()
    return None

def standarlizingBuildingStr(buildingStr:str)->Optional[str]:
    """
    东上 => 东上院
    东中 => 东中院
    陈瑞球 => 陈瑞球楼
    你好 => None
    """
    pattern1 = re.compile(r'^(上|中|下|东上|东中|东下|新上)院?$')
    if pattern1.match(buildingStr) != None:
        building = pattern1.findall(buildingStr)[0]
        building += '院'
        return building
    pattern3 = re.compile(r'^(陈瑞球楼?|球楼?)$')
    if pattern3.match(buildingStr) != None:
        building = '陈瑞球楼'
        return building
    pattern4 = re.compile(r'^工程?馆?$')
    if pattern4.match(buildingStr) != None:
        building = '工程馆'
        return building
    return None


def standarlizingBuildingTimeStr(Str:str)->Optional[Tuple[str, int, int]]:
    """
    东上 3 5 => (东上院,3,5)
    东中 3 5 => (东中院,3,5)
    你好 => None
    """
    pattern1 = re.compile(r'^(上|中|下|东上|东中|东下|新上)院?\s*(\d+)\s+(\d+)$')
    if pattern1.match(Str) != None:
        building, startSection, endSection = pattern1.findall(Str)[0]
        building +='院'
        return building, int(startSection), int(endSection)
    pattern2 = re.compile(r'^(陈瑞球楼?|球楼?)\s*(\d+)\s+(\d+)$')
    if pattern2.match(Str) != None:
        building = '陈瑞球楼'
        _, startSection, endSection = pattern2.findall(Str)[0]
        return building, int(startSection), int(endSection)
    pattern4 = re.compile(r'^(工程?馆?)\s*(\d+)\s+(\d+)$')
    if pattern4.match(Str) != None:
        building = '工程馆'
        _, startSection, endSection = pattern4.findall(Str)[0]
        return building, int(startSection), int(endSection)
    return None

def getWeekDay(targetDate:datetime.date)->str:
    return '星期' + ['一','二','三','四','五','六','日'][targetDate.weekday()]

def getRoomInfo(building:str, room_name:str, savePath:str)->Optional[str]:
    today = datetime.date.today()
    # 1. get building info
    buildingInfo = getSjtuBuilding(building)
    if buildingInfo == None: return None
    try:
        buildingInfo = {room['name']: room for room in buildingInfo['roomList']} 
    except BaseException as e:
        warning('base exception in getRoomInfo-buildingInfo: {}'.format(e))
        return None
    
    # 2. get building course
    buildingCourse = getRoomCourse(building, today)
    if buildingCourse == None: return None
    try:
        roomStudents = {room['roomId']: room['actualStuNum'] for floor in buildingCourse['floorList'] for room in floor.get('roomStuNumbs', [])}            
        buildingCourse = {room['name']: room for floor in buildingCourse['floorList'] for room in floor['children'] }
    except BaseException as e:
        warning('base exception in getRoomInfo-buildingCourse: {}'.format(e))
        return None
        
    # print(buildingCourse)
    # 3. select room
    buildingInfo = buildingInfo.get(room_name, None)
    buildingCourse = buildingCourse.get(room_name, None)
    if buildingInfo == None or buildingCourse == None:
        return None
    roomStudentNum = roomStudents.get(buildingCourse['id'], None)

    # 4. draw picture
    rimg = ResponseImage(
        title='教室信息', 
        titleColor=Colors.PALETTE_SJTU_RED, 
        primaryColor=Colors.PALETTE_SJTU_RED, 
        footer=datetime.datetime.now().strftime("update at %Y-%m-%d %H:%M"),
        layout='normal'
    )
    infoCard = [
        ('title', room_name),
        ('separator',),
        ('body', f"是否为自习教室：{buildingInfo.get('free_room', '--')}\n"
                f"座位数：{buildingInfo.get('zws', '--')}\n"
                f"温度：{buildingInfo.get('sensorTemp', '--')}℃\n"
                f"湿度：{buildingInfo.get('sensorHum', '--')}%\n"
                f"CO2：{buildingInfo.get('sensorCo2', '--')}\n"
                f"PM2.5：{buildingInfo.get('sensorPm25', '--')}\n"
                f"当前人数：{roomStudentNum if roomStudentNum != None else '--'}"
                )
    ]
    rimg.addCard(ResponseImage.RichContentCard(raw_content=infoCard, ))
    courseCard = [('title', '教室课程 - %s'%getWeekDay(today))]
    wa = True # warning only once
    for course in buildingCourse.get('roomCourseList',[]):
        try:
            sjly = course['sjly']
            courseName = course['courseName']
            teacherName = course.get('teacherName', '')
            orgName = course.get('orgName', None)
            startSection = course['startSection']
            endSection = course['endSection']
            startWeek = course['startWeek']
            endWeek = course['endWeek']

            courseTxt = f'【{sjly}】{courseName}  {teacherName}\n' \
                        f'{startSection}-{endSection}节  {startWeek}-{endWeek}周\n'
            if orgName != None: courseTxt += orgName
            # print(courseTxt)
            courseCard.append(('separator', ))
            courseCard.append(('body', courseTxt))
        except BaseException as e:
            if wa:
                warning('base exception in getRoomInfo: {}'.format(e))
                wa = False    
    rimg.addCard(ResponseImage.RichContentCard(raw_content=courseCard, ))
    rimg.generateImage(savePath)
    return savePath

def getRoomRecommend(building:str,startSection:int,endSection:int):
    today = datetime.date.today()
    recommendDict = {}

    if(startSection>=endSection or startSection<0 or endSection>14):
        return None
    # 1.get infomation
    buildingInfo = getSjtuBuilding(building)
    if buildingInfo == None: return None
    try:
        buildingInfo = {room['name']: room for room in buildingInfo['roomList']}  
    except BaseException as e:
        warning('base exception in getRoomRecommend: {}'.format(e))
        return None
    buildingCourse = getRoomCourse(building, today)
    if buildingCourse == None: return None
    try:
        roomStudents = {room['roomId']: room['actualStuNum'] for floor in buildingCourse['floorList'] for room in floor.get('roomStuNumbs', [])} 
        buildingCourse = {room['name']: room for floor in buildingCourse['floorList'] for room in floor['children'] } 
    except BaseException as e:
        warning('base exception in getRoomRecommend-buildingCourse: {}'.format(e))
        return None

    # 2.select the target
    for room_name in buildingCourse.keys():
        # print(room_name)
        flag = True # judge if there is class
        getBuildingCourse = buildingCourse.get(room_name, None)
        getBuildingInfo = buildingInfo.get(room_name, None)
        roomStudentNum = roomStudents.get(getBuildingCourse['id'], None)
        if getBuildingInfo == None or getBuildingCourse == None:
            return None
        for course in getBuildingCourse.get('roomCourseList',[]):
            start_section = course['startSection']
            end_section = course['endSection']
            if(((start_section>=startSection) and (start_section<=endSection)) or ((end_section>=startSection) and(end_section<=endSection) )):
                flag = False
                break
        if flag:
            roomInfo = {}
            roomInfo['People'] = roomStudentNum if roomStudentNum != None else '--'            
            roomInfo['CO2']=getBuildingInfo.get('sensorCo2', '--')
            roomInfo['Temp']=getBuildingInfo.get('sensorTemp', '--')
            roomInfo['Hum']=getBuildingInfo.get('sensorHum', '--')
            recommendDict[room_name] = roomInfo

    # 3.draw the picture
    rimg = ResponseImage(
        title='教室推荐', 
        titleColor=Colors.PALETTE_SJTU_RED, 
        primaryColor=Colors.PALETTE_SJTU_RED, 
        footer=datetime.datetime.now().strftime("update at %Y-%m-%d %H:%M"),
        layout='normal'
    )
    recommendCard = [('title', '教室推荐 - %s'%building)]
    # print(recommendDict)
    if(len(recommendDict)>25):
        count = 0
        for room_name,roomInfo in recommendDict.items():
            if(count>25):break
            try:
                recommendTxt = f"所选教学楼在第{startSection}-{endSection}节有空闲教室：{room_name}\n" \
                            f"本教室当前温度为：{roomInfo['Temp']}℃ ，湿度为：{roomInfo['Hum']}% ，CO2浓度为{roomInfo['CO2']}，室内人数为{roomInfo['People']}\n"
                recommendCard.append(('separator', ))
                recommendCard.append(('body', recommendTxt))
            except BaseException as e:
                    warning('base exception in getRoomRecommend: {}'.format(e))
            count += 1
    else:
        for room_name,roomInfo in recommendDict.items():
            try:
                recommendTxt = f"所选教学楼在第{startSection}-{endSection}节有空闲教室：{room_name}\n" \
                            f"本教室当前温度为：{roomInfo['Temp']}℃ ，湿度为：{roomInfo['Hum']}% ，CO2浓度为{roomInfo['CO2']}，室内人数为{roomInfo['People']}\n"
                recommendCard.append(('separator', ))
                recommendCard.append(('body', recommendTxt))
            except BaseException as e:
                    warning('base exception in getRoomRecommend: {}'.format(e))

    rimg.addCard(ResponseImage.RichContentCard(raw_content=recommendCard, ))
    savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'Roomrecommend.png')
    rimg.generateImage(savePath)
    return savePath


def processJsInfo(jsInfo: Dict[str, List[Dict[str, Any]]]) -> List[Tuple[str, List[bool]]]:
    result:List[Tuple[str, List[bool]]] = []
    for floor in jsInfo.get('floorList', []):
        for room in floor.get('children', {}):
            roomName:str = room.get('name', 'unknow')
            roomSecs = [False] * 15 # 是否有课
            for course in room.get('roomCourseList', []):
                startSec:int = course.get('startSection', 0)
                endSec:int = course.get('endSection', 0)
                for sec in range(startSec, endSec + 1):
                    roomSecs[sec] = True # TODO: IndexError
            result.append((roomName, roomSecs))
    return sorted(result, key=lambda x: x[0])

def drawJs(jsInfo: List[Tuple[str, List[bool]]], targetBuilding: str, savePath: str) -> Optional[str]:
    img = ResponseImage(
        title=f'教室空闲时间',
        titleColor=PALETTE_SJTU_RED,
        primaryColor=PALETTE_SJTU_RED,
    )

    # sub img
    cell_size = 50
    padding = 10
    width = (len(jsInfo[0][1]) - 2) * (cell_size + padding) + 100
    height = (len(jsInfo) - 1) * (cell_size + padding)
    sub_img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(sub_img)

    for i, (room_name, availability) in enumerate(jsInfo):
        draw.text((0, i * cell_size + i * padding + 12), room_name.replace(targetBuilding, ""), fill="black", font = FONT_SYHT_M28)

        for j, available in enumerate(availability[1:]):
            color = PALETTE_GREY_BORDER if available else PALETTE_GREEN
            draw_rounded_rectangle(
                sub_img,
                (
                    j * cell_size + j * padding + 100,
                    i * cell_size + i * padding,
                    (j + 1) * cell_size + j * padding + 100,
                    (i + 1) * cell_size + i * padding,
                ),
                fill=color
            )

    time_slots = [
        "08:00-08:45",
        "08:55-09:40",
        "10:00-10:45",
        "10:55-11:40",
        "12:00-12:45",
        "12:55-13:40",
        "14:00-14:45",
        "14:55-15:40",
        "16:00-16:45",
        "16:55-17:40",
        "18:00-18:45",
        "18:55-19:40",
        "20:00-20:45",
        "20:55-21:40"
    ]

    time_axis_img = Image.new("RGB", (200, width), "white")
    draw = ImageDraw.Draw(time_axis_img)
    for i, time in enumerate(time_slots):
        bbox = FONT_SYHT_M28.getbbox(time)
        left = 200 - bbox[2] + bbox[0]
        draw.text((left, i * cell_size + i * padding + 112), time, fill="black", font = FONT_SYHT_M28)
    time_axis_img = time_axis_img.rotate(90, expand=True)

    img.addCard(
        ResponseImage.RichContentCard(
            raw_content=[
                ('title', f"目标楼栋: {targetBuilding}"),
                ('subtitle', f"{datetime.datetime.now().strftime('%Y-%m-%d')}，绿色为空闲"),
                ('separator', ''),
                ('illustration', sub_img),
                ('illustration', time_axis_img),
                ('text', '\n')
            ]
        )
    )
    

    img.generateImage(savePath)
    return savePath

class SjtuJsQuery(StandardPlugin):
    def __init__(self) -> None:
        self.triggerPattern = re.compile(r'^-js\s+(.*)$')
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return self.triggerPattern.match(msg) != None
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        buildingStr = standarlizingBuildingStr(self.triggerPattern.findall(msg)[0])
        if buildingStr == None:
            send(target, '教学楼解析错误，请重新输入要查询的教学楼，例如："-js 东上"、"-js 下院"、"-js 东中"。\n'
                         '您也可以尝试其他命令，例如：\n'
                         '1. "教室 东下305" 查询教室人数、温度、全日课程等情况\n'
                         '2. "教室推荐 东下 3 5" 查询东下院3节到5节间无课的空教室\n'
                         '3. "教室人数 东下" 查询当前东下院各教室人数\n'
                         '4. "-jsrsls 东下305" 查询近一周该教室人流量', data['message_type'])
            return "OK"
        savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'js-%d-%s.png'%(target, buildingStr))
        jsInfo = processJsInfo(getRoomCourse(buildingStr, datetime.date.today()))
        courseImgPath = drawJs(jsInfo, buildingStr, savePath)
        if courseImgPath == None:
            send(target, f'[CQ:reply,id={data["message_id"]}]图片绘制失败', data['message_type'])
        else:
            send(target, '[CQ:image,file=file:///%s]'%courseImgPath, data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'SjtuClassroom',
            'description': '教学楼空闲查询',
            'commandDescription': '-js [东上/东中/...]',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
        
    def checkSelfStatus(self):
        if getRoomCourse('东中院', datetime.date.today()) != None:
            return 1, 1, '正常'
        else:
            return 1, 0, "获取东中院信息失败"
            
        
class SjtuClassroom(StandardPlugin):
    def __init__(self) -> None:
        self.triggerPattern = re.compile(r'^(教室|教室查询)\s+(.*)$')
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return self.triggerPattern.match(msg) != None
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        _, roomStr = self.triggerPattern.findall(msg)[0]
        result = standarlizingRoomStr(roomStr)
        if result == None:
            send(target, '教室参数解析错误，请重新输入查询参数，例如："教室 东上105"、"教室 东下院311"、"教室 东中1-102"\n'
                '您也可以尝试其他命令，例如：\n'
                '1. "-js 东下" 绘制东下今日教室空闲情况\n'
                '2. "教室推荐 东下 3 5" 查询东下院3节到5节间无课的空教室\n'
                '3. "教室人数 东下" 查询当前东下院各教室人数\n'
                '4. "-jsrsls 东下305" 查询近一周该教室人流量', data['message_type'])
            return "OK"
        building, room_name = result
        savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'course-%d-%s.png'%(target, room_name))
        courseImgPath = getRoomInfo(building, room_name, savePath)
        if courseImgPath == None:
            send(target, f'[CQ:reply,id={data["message_id"]}]未查询到教室信息，可能结果是：不存在该教室', data['message_type'])
        else:
            send(target, '[CQ:image,file=file:///%s]'%courseImgPath, data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'SjtuClassroom',
            'description': '教室查询',
            'commandDescription': '教室 [东上院102/东中1-105/...]',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }

class SjtuClassroomRecommend(StandardPlugin):
    def __init__(self) -> None:
        self.triggerPattern = re.compile(r'(推荐|教室推荐)\s+(.*)$')
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return self.triggerPattern.match(msg) != None
    def executeEvent(self,msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        _,Str = self.triggerPattern.findall(msg)[0]
        result = standarlizingBuildingTimeStr(Str)
        if result == None:
            send(target, '教室推荐参数解析错误，请重新输入查询参数，例如："教室推荐 东上 3 5"、"教室推荐 东下 5 8"\n'
                         '您也可以尝试其他命令，例如：\n'
                         '1. "教室 东下305" 查询教室人数、温度、全日课程等情况\n'
                         '2. "-js 东下" 绘制东下今日教室空闲情况\n'
                         '3. "教室人数 东下" 查询当前东下院各教室人数\n'
                         '4. "-jsrsls 东下305" 查询近一周该教室人流量', data['message_type'])
            return "OK"
        building, startSection, endSection = result
        courseImgPath = getRoomRecommend(building,startSection,endSection)
        if courseImgPath == None:
            send(target, f'[CQ:reply,id={data["message_id"]}]未查询到教室信息，可能结果是：不存在空闲教室或命令格式错误', data['message_type'])
        else:
            send(target, '[CQ:image,file=file:///%s]'%courseImgPath, data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'SjtuClassroomRecommend',
            'description': '教室推荐',
            'commandDescription': '教室推荐 东上 3 5',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'jmh',
        }

class SjtuClassroomPeopleNum(StandardPlugin):
    def __init__(self):
        self.triggerPattern = re.compile('^教室人数\s*(.*)$')
    def judgeTrigger(self, msg:str, data:Any)->bool:
        return self.triggerPattern.match(msg) != None
    def executeEvent(self, msg:str, data:Any):
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        buildingStr = standarlizingBuildingStr(self.triggerPattern.findall(msg)[0])
        if buildingStr == None:
            send(target, f'[CQ:reply,id={data["message_id"]}]教学楼解析错误，请重新输入查询参数，例如：'
                          '"教室人数 东上"、"教室人数 东下院"、"教室人数 球楼"\n'
                          '您也可以尝试其他命令，例如：\n'
                          '1. "教室 东下305" 查询教室人数、温度、全日课程等情况\n'
                          '2. "教室推荐 东下 3 5" 查询东下院3节到5节间无课的空教室\n'
                          '3. "-js 东下" 绘制东下今日教室空闲情况\n'
                          '4. "-jsrsls 东下305" 查询近一周该教室人流量',
                          data['message_type'])
            return 'OK'
        now = datetime.datetime.now()
        # 2. get building course
        buildingCourse = getRoomCourse(buildingStr, now.date())
        if buildingCourse == None:
            send(target, f'[CQ:reply,id={data["message_id"]}]网络错误，请稍后重试', data['message_type'])
            return 'OK'
        try:
            roomStudents = {room['roomId']: int(room['actualStuNum']) for floor in buildingCourse['floorList'] for room in floor.get('roomStuNumbs', [])}            
            rooms = {room['name']: room for floor in buildingCourse['floorList'] for room in floor['children'] }
        except BaseException as e:
            warning('base exception in SjtuClassroomPeopleNum: {}'.format(e))
            send(target, f'[CQ:reply,id={data["message_id"]}]API回传参数解析错误', data['message_type'])
            return 'OK'

        roomList = []
        # '东上院101' => ('东上院', '101')
        # '东中院1-105' => ('东中院', '1-105')
        roomNamePattern = re.compile(r'^(\D*)(.*)$')
        for roomName, roomInfo in rooms.items():
            _, roomNum = roomNamePattern.findall(roomName)[0]
            roomId = roomInfo['id']
            if roomId in roomStudents.keys():
                numStudents = roomStudents[roomId]
                # numStudents = random.randint(1, 40)
                if numStudents < 5: color = 'green'
                elif numStudents < 15: color = 'blue'
                elif numStudents < 30: color = 'orange'
                else: color = 'red'
                roomList.append((roomNum, numStudents, numStudents, color))
            else:
                roomList.append((roomNum, 0, 'null', 'grey'))
        
        # draw bar fig
        plt.figure(figsize=(3, len(roomList)/5)) 
        roomNum, numStudents, yLabel, color = zip(*sorted(roomList, key=lambda x: x[0], reverse=True))
        bar = plt.barh(roomNum, numStudents, color=color)
        plt.bar_label(bar, yLabel, fontsize=8)
        # plt.ylabel('classroom')
        plt.xlabel('number of people')
        plt.xlim(left=0)
        plt.ylim(-1, len(roomList))
        fig = BytesIO()
        plt.savefig(fig, dpi=400, bbox_inches='tight', pad_inches=0)
        # draw response image
        card = ResponseImage(
            titleColor=Colors.PALETTE_SJTU_BLUE,
            title='教室人数',
            layout='normal',
            width=880,
        )
        card.addCard(ResponseImage.RichContentCard(raw_content=[
            ('title', buildingStr + now.strftime('    %Y-%m-%d  %H:%M')),
            ('illustration', fig)
        ]))
        
        # save response image
        savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'classroomPeopleNum-%d.png'%target)
        card.generateImage(savePath)
        send(target, '[CQ:image,file=file:///%s]'%savePath, data['message_type'])
        return 'OK'
    def getPluginInfo(self, )->Any:
        return {
            'name': 'SjtuClassroomPeopleNum',
            'description': '教室人数',
            'commandDescription': '教室人数 [教学楼]',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
    