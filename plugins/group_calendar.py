from utils.basic_configs import *
from utils.basic_event import *
from typing import Union, Tuple, Any, List, Optional
from utils.standard_plugin import StandardPlugin, CronStandardPlugin
import mysql.connector
from utils.response_image_beta import *
import re
from threading import Semaphore
import datetime
from utils.sql_utils import newSqlSession
from pymysql.converters import escape_string

def createCalendarTable():
    mydb, mycursor = newSqlSession()
    mycursor.execute("""create table if not exists `groupCalendar` (
        `group_id` bigint unsigned not null,            # 群号
        `uid` bigint unsigned not null,                 # 每个群的事件唯一id,不同群可重复
        `create_time` timestamp not null,               # 事件创建的时间戳
        `last_update_time` timestamp not null,          # 最近一次更改时间戳
        `create_user_id` bigint unsigned not null,      # 事件创建者
        `event_tag` char(30) default null,              # 事件自定义tag, 群内尚未overdue的唯一, 不同群可重复
        `event_description` varchar(500) default null,  # 事件描述
        `event_schedule_time` timestamp not null,       # 事件预计执行时间
        `need_remind` bool not null default false,      # 事件是否需要提醒
        `overdue` bool not null default false,          # 事件是否过期
        `reminded_users` json default null,             # 被提醒对象
        primary key (`group_id`, `uid`),
        index(`group_id`, `event_tag`)
    )charset=utf8mb4, collate=utf8mb4_unicode_ci;""")

class GroupCalendarHelper(StandardPlugin):
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg in ['日历帮助', 'sched help'] and data['message_type']=='group'
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        group_id = data['group_id']
        send(group_id, 'test')
        return 'OK'
    def getPluginInfo(self) -> dict:
        return {
            'name': 'GroupCalendarHelper',
            'description': '日历帮助',
            'commandDescription': '日历帮助/sched help',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
class StrToDate():
    pattern1 = re.compile(r'^(\d+)(\s|\-|\/|\\|\.|\~)(\d+)(\s|\-|\/|\\|\.|\~)(\d+)$')
    pattern2 = re.compile(r'^(\d{2}|\d{4})(\d{2})(\d{2})$')
    pattern3 = re.compile(r'^(\d+)(\s|\-|\/|\\|\.|\~)(\d+)$')
    pattern4 = re.compile(r'^(\d+)\:(\d+)$')
    pattern5 = re.compile(r'^(\d+)(\s|\-|\/|\\|\.|\~)(\d+)(\s|\-|\/|\\|\.|\~)(\d+)(\s|\-|\/|\\|\.|\~)+(\d+)\:(\d+)$')
    pattern6 = re.compile(r'^(\d{2}|\d{4})(\d{2})(\d{2})(\s|\-|\/|\\|\.|\~)+(\d+)\:(\d+)$')
    @staticmethod
    def convert(d:str)->Optional[datetime.datetime]:
        now = datetime.datetime.now()
        try:
            if StrToDate.pattern1.match(d) != None:
                yy, _, mm, _, dd = StrToDate.pattern1.findall(d)[0]
                yy, mm, dd = int(yy), int(mm), int(dd)
                if yy < 100:
                    yy += 2000
                return datetime.datetime(year=yy, month=mm, day=dd)
            if StrToDate.pattern2.match(d) != None:
                yy, mm, dd = StrToDate.pattern2.findall(d)[0]
                yy, mm, dd = int(yy), int(mm), int(dd)
                if yy < 100:
                    yy += 2000
                return datetime.datetime(year=yy, month=mm, day=dd)
            if StrToDate.pattern3.match(d) != None:
                mm, dd = StrToDate.pattern3.findall(d)[0]
                mm, dd = int(mm), int(dd)
                return datetime.datetime(year=now.year, month=mm, day=dd)
            if StrToDate.pattern4.match(d) != None:
                HH, MM = StrToDate.pattern4.findall(d)[0]
                HH, MM = int(HH), int(MM)
                return datetime.datetime(year=now.year,month=now.month,day=now.day,hour=HH,minute=MM)
            if StrToDate.pattern5.match(d) != None:
                yy, _, mm, _, dd, _, HH, MM = StrToDate.pattern5.findall(d)[0]
                yy, mm, dd = int(yy), int(mm), int(dd)
                HH, MM = int(HH), int(MM)
                if yy < 100:
                    yy += 2000
                return datetime.datetime(year=yy,month=mm,day=dd,hour=HH,minute=MM)
            if StrToDate.pattern6.match(d) != None:
                yy, mm, dd, _, HH, MM = StrToDate.pattern6.findall(d)[0]
                yy, mm, dd = int(yy), int(mm), int(dd)
                HH, MM = int(HH), int(MM)
                if yy < 100:
                    yy += 2000
                return datetime.datetime(year=yy,month=mm,day=dd,hour=HH,minute=MM)
            return None
        except ValueError:
            return None
        except BaseException as e:
            warning('base exception in StrToDate: {}'.format(e))
            return None

def datetimeToStr(d: datetime.datetime)->str:
    return d.strftime("%y-%m-%d/%H:%M:%S")

def strToUsers(u:str)->List[int]:
    """parse string like:\\
        '1,2,3' => [1, 2, 3]\\
        '[CQ:at,id=1],2,[CQ:at,id=3]' => [1, 2, 3]
    """
    # 匹配前面不是t的英文逗号和其他分隔符
    us = re.split(r'(?<!t)\,|\.|，|\。|\/|\\|-|\s', u)
    pattern1 = re.compile(r'^(\d+)')
    pattern2 = re.compile(r'^\[CQ\:at\,qq\=(\d+)\]')
    result = []
    for u in us:
        if pattern1.match(u) != None:
            result.append(int(pattern1.findall(u)[0]))
        elif pattern2.match(u) != None:
            result.append(int(pattern2.findall(u)[0]))
    return result

def updateGroupCalendar(
    group_id: int,
    uid: Optional[int],
    create_time: datetime.datetime,
    create_user_id: int,
    event_tag: Optional[str],
    event_description: Optional[str],
    even_schedule_time: datetime.datetime,
    need_remind: bool=False,
    overdue: bool=False,
    reminded_users: Optional[List[int]]=None
)->Tuple[bool, Dict[str, Any]]:
    """数据库io函数，上层调用此函数即可
    @return:
        if succ: (True, (int)uid)
        else:    (False, (str)errLog)
    注意：
        uid和event_tag不可同时用于定位，因此当两者都不是None时默认用uid定位来修改event_tag
    """
    try:
        if not isinstance(group_id, int):
            raise ValueError('group_id should be an instance of int')
        if not isinstance(create_time, datetime.datetime):
            raise ValueError('create_time should be an instance of datetime')
        if not isinstance(need_remind, bool):
            raise ValueError('need_remind should be an instance of bool')
        if not isinstance(overdue, bool):
            raise ValueError('overdue should be an instance of bool')
        mydb, mycursor = newSqlSession()
        event_description_sentence = f", event_description = '{escape_string(event_description)}'" if event_description else ''
        event_tag_sentence = f", event_tag = '{escape_string(event_tag)}'" if event_tag else ''
        reminded_users_sentence = f", reminded_users = cast('{escape_string(json.dumps(reminded_users))}' as json)" if reminded_users != None else ''
        if isinstance(uid, int):
            mycursor.execute(f"""update `groupCalendar`
            set
                last_update_time = '{datetimeToStr(create_time)}',
                need_remind = {need_remind},
                overdue = {overdue}
                {event_tag_sentence}
                {event_description_sentence}
                {reminded_users_sentence}
            where
                group_id = {group_id} and
                uid = {uid}
            """)
            return True, {'uid': uid,}
        elif isinstance(event_tag, str):
            mycursor.execute(f"select ifnull(max(`uid`)+1,0) from `groupCalendar` where group_id={group_id}")
            uid, = list(mycursor)[0]
            mycursor.execute(f"""insert into `groupCalendar` set
                group_id = {group_id},
                uid = {uid},
                create_time = '{datetimeToStr(create_time)}',
                last_update_time = '{datetimeToStr(create_time)}',
                create_user_id = {create_user_id},
                event_tag = '{escape_string(event_tag)}',
                event_description = {'null' if event_description == None else f"'{escape_string(event_description)}'"},
                event_schedule_time = '{datetimeToStr(even_schedule_time)}',
                need_remind = {need_remind},
                overdue = {overdue},
                reminded_users = cast('{escape_string(json.dumps(reminded_users))}' as json)
            on duplicate key update event_tag = '{event_tag}'""")
            return True, {'uid':uid}
    except mysql.connector.Error as e:
        warning('mysql error in updateGroupCalendar: {}'.format(e))
        return False, {'err':str(e)}
    except ValueError as e:
        return False, {'err':str(e)}
    except BaseException as e:
        warning('base exception in updateGroupCalendar: {}'.format(e))
        return False, {'err':str(e)}
    return False, {'err':'event_tag or uid type error'}

class GroupCalendarManager(StandardPlugin):
    semaphore = Semaphore()
    def __init__(self) -> None:
        self.findModPattern = re.compile(r'^\-?sched\s+(\S+)\s+(.*)$')
        self.modMap = {
            'add': GroupCalendarManager.schedAdd,
            'new': GroupCalendarManager.schedAdd,
            'tag': GroupCalendarManager.schedTag,
            'show': GroupCalendarManager.schedShow,
            'edit': GroupCalendarManager.schedEdit,
        }
        if GroupCalendarManager.semaphore.acquire(blocking=False):
            createCalendarTable()
    def loadEventFromSql(self):
        pass
    @staticmethod
    def schedAdd(cmd:str, data):
        group_id = data['group_id']
        user_id = data['user_id']
        create_time = datetime.datetime.fromtimestamp(data['time'])
        eventScheduledTime = datetime.datetime.today() + datetime.timedelta(days=1)
        eventScheduleDescription = None
        remind = False
        reminded_users = []
        uid = None
        tag = None
        cmds = re.split(r'\s', cmd)

        idx = 0
        while idx < len(cmds):
            arg = cmds[idx]
            if arg in ['-t', '--time']:
                idx += 1
                eventScheduledTime = StrToDate.convert(cmds[idx])
                if eventScheduledTime == None:
                    send(group_id, '[CQ:reply,id=%d]日期格式解析错误，日期格式示范：\n1999-12-31/23:59'%data['message_id'])
                    return
            elif arg in ['-d', '--descript']:
                idx += 1
                eventScheduleDescription = cmds[idx]
            elif arg in ['-r', '--remind']:
                remind = True
            elif arg in ['-g', '--tag']:
                idx += 1
                tag = cmds[idx]
            elif arg in ['-i', '--uid']:
                idx += 1
                uid = int(cmds[idx])
            elif arg in ['-u', '--users']:
                idx += 1
                reminded_users += strToUsers(cmds[idx])
            idx += 1
        overdue = eventScheduledTime < create_time
        succ, info = updateGroupCalendar(
            group_id=group_id,
            uid=uid,
            create_time=create_time,
            create_user_id=user_id,
            event_tag=tag,
            event_description=eventScheduleDescription,
            even_schedule_time=eventScheduledTime,
            need_remind=remind,
            overdue=overdue,
            reminded_users=reminded_users
        )
        if succ:
            send(group_id, 
                f"[CQ:reply,id={data['message_id']}]添加成功，参数如下:\n"
                f"uid={info['uid']}\ncreate_time={datetimeToStr(create_time)}\n"
                f"event_schedule_time={datetimeToStr(eventScheduledTime)}\n"
                f"event_tag={tag if tag else '`None`'}\n"
                f"event_description={eventScheduleDescription}\n"
                f"need_remind={remind}\n"
                f"remind_users={json.dumps(reminded_users)}")
        else:
            send(group_id, f"[CQ:reply,id={data['message_id']}]添加失败，错误信息:\n{info['err']}")
    
    schedTagPattern = re.compile(r'^(\d+)\s+(\S+)$')
    @staticmethod
    def schedTag(cmd:str, data):
        group_id = data['group_id']
        create_time = datetime.datetime.fromtimestamp(data['time'])
        if GroupCalendarManager.schedTagPattern.match(cmd) == None:
            send(group_id, '输入格式不对哦，请输入【日历帮助】获取操作指南')
            return
        uid, tag = GroupCalendarManager.schedTagPattern.findall(cmd)[0]
        succ, info = updateGroupCalendar(group_id=group_id,create_time=create_time,event_tag=tag)

    
    @staticmethod
    def schedShow(cmd:str, data):
        pass
    @staticmethod
    def schedEdit(cmd:str, data):
        pass

    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return self.findModPattern.match(msg) != None and data['message_type']=='group'
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        mod, cmd = self.findModPattern.findall(msg)[0]
        if mod in self.modMap.keys():
            self.modMap[mod](cmd, data)
        else:
            send(data['group_id'], '输入格式不对哦，请输入【日历帮助】获取操作指南')
        return 'OK'
    def getPluginInfo(self) -> dict:
        return {
            'name': 'GroupCalendarHelper',
            'description': '日历管理',
            'commandDescription': 'sched <mod> [...]',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': ['groupCalendar'],
            'version': '1.0.0',
            'author': 'Unicorn',
        }