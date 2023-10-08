from utils.standard_plugin import StandardPlugin
from utils.basic_configs import ROOT_PATH, SAVE_TMP_PATH
import requests
from utils.basic_event import send, warning
import re
from typing import List, Tuple, Optional, Union, Dict, Any
import requests
import datetime
from utils.response_image_beta import ResponseImage
from utils.hot_search_image import HotSearchImage, Colors, Fonts
import os.path
from matplotlib import pyplot as plt
from io import BytesIO

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
        return building, building+roomCode
    pattern3 = re.compile(r'^(陈瑞球楼?|球楼?)\s*(\d{3})$')
    if pattern3.match(roomStr) != None:
        building = '陈瑞球楼'
        _, roomCode = pattern3.findall(roomStr)[0]
        return building, building + roomCode
    return None

def standarlizingBuildingStr(buildingStr:str)->Optional[str]:
    """
    东上 => 东上院
    东中 => 东中院
    陈瑞球 => 陈瑞球楼
    你好 => None
    """
    pattern1 = re.compile(r'^(上|中|下|东上|东中|东下)院?$')
    if pattern1.match(buildingStr) != None:
        building = pattern1.findall(buildingStr)[0]
        building += '院'
        return building
    pattern3 = re.compile(r'^(陈瑞球楼?|球楼?)$')
    if pattern3.match(buildingStr) != None:
        building = '陈瑞球楼'
        return building
    return None


def standarlizingBuildingTimeStr(Str:str)->Optional[str]:
    """
    东上 3 5 => (东上院,3,5)
    东中 3 5 => (东中院,3,5)
    你好 => None
    """
    pattern1 = re.compile(r'^(上|中|下|东上|东中|东下)院?\s*(\d+)\s+(\d+)$')
    if pattern1.match(Str) != None:
        building,startSection,endSection = pattern1.findall(Str)[0]
        building +='院'
        return building,startSection,endSection
    pattern2 = re.compile(r'^(陈瑞球楼?|球楼?)\s*(\d+)\s+(\d+)$')
    if pattern2.match(Str) != None:
        building = '陈瑞球楼'
        _,startSection,endSection = pattern2.findall(Str)[0]
        return building,startSection,endSection
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


def getRoomrecommend():
    # get room recommend info

    today = datetime.date.today()
    date = getRoomDate()
    section = date['section']
    buildings = ['上院','中院','下院','东下院','东中院']
    recommendDict = {}
    for building in buildings:
        # 2.get room info pre

        buildingInfo = getSjtuBuilding(building)
        if buildingInfo == None: return None
        try:
            buildingInfo = {room['name']: room for room in buildingInfo['roomList']} 
        except BaseException as e:
            warning('base exception in getRoomRecommend: {}'.format(e))
            return None
        # 3.get room course

        buildingCourse = getRoomCourse(building, today)
        if buildingCourse == None: return None
        try:
            buildingCourse = {room['name']: room for floor in buildingCourse['floorList'] for room in floor['children'] }
        except BaseException as e:
            warning('base exception in getRoomRecommend-buildingCourse: {}'.format(e))
            return None
        for room_name in buildingCourse.keys():
            # print(room_name)
            flag = True # judge if there is class
            EndSection = 0
            getBuildingCourse = buildingCourse.get(room_name, None)
            getBuildingInfo = buildingInfo.get(room_name, None)
            if getBuildingInfo == None or getBuildingCourse == None:
                return None
            for course in getBuildingCourse.get('roomCourseList',[]):
                endSection = course['endSection']
                if(EndSection < endSection):EndSection = endSection
                if (endSection > section):
                    flag = False
                    break
            if flag:
                roomInfo = {}
                roomInfo['endSection']=EndSection
                roomInfo['CO2']=getBuildingInfo.get('sensorCo2', '--')
                roomInfo['Temp']=getBuildingInfo.get('sensorTemp', '--')
                roomInfo['Hum']=getBuildingInfo.get('sensorHum', '--')
                recommendDict[room_name] = roomInfo


    # 2.draw picture
    rimg = ResponseImage(
    title='教室推荐', 
    titleColor=Colors.PALETTE_SJTU_RED, 
    primaryColor=Colors.PALETTE_SJTU_RED, 
    footer=datetime.datetime.now().strftime("update at %Y-%m-%d %H:%M"),
    layout='normal'
    )
    recommendCard = [('title', '教室推荐 - %s'%getWeekDay(today))]
    # print(recommendDict)
    matchPattern = re.compile(r'^(上院|中院|下院)')
    if(len(recommendDict)>25):
        count = 0
        for room_name,roomInfo in recommendDict.items():
            if(matchPattern.match(room_name)):
                continue
            if(count>25):break
            try:
                if(roomInfo['endSection']==0):
                    recommendTxt = f"空闲教室：{room_name}  本日该教室无课\n" \
                                f"本教室当前温度为：{roomInfo['Temp']}℃ ，湿度为：{roomInfo['Hum']}% ，CO2浓度为{roomInfo['CO2']}\n"
                else:
                    recommendTxt = f"空闲教室：{room_name}  本日最后一节课为第{roomInfo['endSection']}节\n" \
                                f"本教室当前温度为：{roomInfo['Temp']}℃ ，湿度为：{roomInfo['Hum']}% ，CO2浓度为{roomInfo['CO2']}\n"
                recommendCard.append(('separator', ))
                recommendCard.append(('body', recommendTxt))
            except BaseException as e:
                    warning('base exception in getRoomRecommend: {}'.format(e))
            count += 1
    else:
        for room_name,endSection in recommendDict.items():
            try:
                if(roomInfo['endSection']==0):
                    recommendTxt = f"空闲教室：{room_name}  本日该教室无课\n" \
                                f"本教室当前温度为：{roomInfo['Temp']}℃ ，湿度为：{roomInfo['Hum']}% ，CO2浓度为{roomInfo['CO2']}\n"
                else:
                    recommendTxt = f"空闲教室：{room_name}  本日最后一节课为第{roomInfo['endSection']}节\n" \
                                f"本教室当前温度为：{roomInfo['Temp']}℃ ，湿度为：{roomInfo['Hum']}% ，CO2浓度为{roomInfo['CO2']}\n"
                recommendCard.append(('separator', ))
                recommendCard.append(('body', recommendTxt))
            except BaseException as e:
                    warning('base exception in getRoomRecommend: {}'.format(e))

    rimg.addCard(ResponseImage.RichContentCard(raw_content=recommendCard, ))
    savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'Roomrecommend.png')
    rimg.generateImage(savePath)
    return savePath


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
            send(target, '教室参数解析错误，请重新输入查询参数，例如：\n"教室 东上105"、"教室 东下院311"、"教室 东中1-102"', data['message_type'])
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
            send(target, '教室推荐参数解析错误，请重新输入查询参数，例如：\n"教室推荐 东上 3 5"、"教室推荐 东下 5 8"', data['message_type'])
            return "OK"
        building,startSection,endSection = result
        startSection = int(startSection)
        endSection = int(endSection)
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
            send(target, f'[CQ:reply,id={data["message_id"]}]教学楼解析错误，请重新输入查询参数，例如：\n'
                          '"教室人数 东上"、"教室人数 东下院"、"教室人数 球楼"',
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
    