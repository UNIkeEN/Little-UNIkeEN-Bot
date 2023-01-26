## 1. 插件简介

| 插件名称 | 父类 | 触发关键词 | 触发权限 | 内容 |
| ---- | ---- | ---- | ---- | ---- |
| SjtuClassroom | StandardPlugin | '教室 \[东上院102/东中1-105/...\]' | None | 教室查询 |

## 2. 样例分析

```
111> 教室 东上102
bot>【回复上文】
    上海交通大学/闵行校区/东上院/一层/东上院102
    是否空闲：0
    座位数：45
    温度：--℃
    湿度：--%
    CO2：--
    PM2.5：--

222> 教室 东中102
bot> 教室参数解析错误，请重更新输入查询参数，例如：
"教室 东上105"、"教室 东下院311"、"教室 东中1-102"

333> 教室 东中1-102
bot> 【回复上文】未查询到教室信息，可能结果是：不存在该教室
```

## 3. 代码分析

代码位于 `plugins/sjtuClassroom.py`

```python
headers = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Connection": "keep-alive",
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
    session = requests.session()
    session.get(url)
    session.get("https://jaccount.sjtu.edu.cn")
    req = session.post(url=url, headers=headers, data=data)
    if req.status_code != requests.codes.ok:
        warning("sjtu classroom API failed!")
        return None
    try:
        result = req.json()
        if result['code'] != 200:
            warning("code != 200, sjtu classroom API failed!")
            return None
        print(result)
        return result['data']
    except requests.JSONDecodeError as e:
        warning('json decode error while getting sjtu classroom: {}'.format(e))
    except BaseException as e:
        warning('base exception while getting sjtu classroom: {}'.format(e))
    return None

def standarlizingRoomStr(roomStr:str)->Optional[Tuple[str, str]]:
    """
    东上103 => (东上院, 东上院103)
    东中1-105 => (东中院, 东中院1-105)
    你好 => None
    """
    pattern1 = re.compile(r'^(上|中|下|东上|东下|)院?\s*(\d{3})$')
    if pattern1.match(roomStr) != None:
        building, roomCode = pattern1.findall(roomStr)[0]
        building += '院'
        return building, building + roomCode
    pattern2 = re.compile(r'^东中(院?\s*)(\d\-\d{3})$')
    if pattern2.match(roomStr):
        building = '东中院'
        _, roomCode = pattern2.findall(roomStr)[0]
        return building, building+roomCode
    return None

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
            send(target, '教室参数解析错误，请重更新输入查询参数，例如：\n"教室 东上105"、"教室 东下院311"、"教室 东中1-102"', data['message_type'])
            return "OK"
        building, room_name = result
        building_info = getSjtuBuilding(building)
        if building_info == None:
            send(target, f'[CQ:reply,id={data["message_id"]}]cookie失效，请提醒管理员维护此功能', data['message_type'])
            return 'OK'
        roomList = building_info['roomList']
        
        text = f'[CQ:reply,id={data["message_id"]}]'
        for room in roomList:
            if room['name'] == room_name:
                text += (
                    f"{room.get('fullName', '--')}\n"
                    f"是否空闲：{room.get('free_room', '--')}\n"
                    f"座位数：{room.get('zws', '--')}\n"
                    f"温度：{room.get('sensorTemp', '--')}℃\n"
                    f"湿度：{room.get('sensorHum', '--')}%\n"
                    f"CO2：{room.get('sensorCo2', '--')}\n"
                    f"PM2.5：{room.get('sensorPm25', '--')}"
                )
                send(target, text, data['message_type'])
                return "OK"

        send(target, f'[CQ:reply,id={data["message_id"]}]未查询到教室信息，可能结果是：不存在该教室', data['message_type'])
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
```