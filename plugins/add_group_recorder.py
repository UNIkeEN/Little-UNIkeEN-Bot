from utils.standard_plugin import AddGroupStandardPlugin, CronStandardPlugin
from utils.basic_event import get_group_system_msg, warning
from utils.sql_utils import newSqlSession
from typing import Any, Union, List, Dict, Tuple
import mysql.connector
from threading import Semaphore
import datetime

class AddGroupRecorder(AddGroupStandardPlugin, CronStandardPlugin):
    initOnceGuard = Semaphore()
    def __init__(self) -> None:
        if self.initOnceGuard.acquire(blocking=False):
            mydb, mycursor = newSqlSession()
            mycursor.execute("""
            create table if not exists `addGroupRecord` (
                `sub_type` char(20),
                `group_id` bigint unsigned not null,
                `user_id` bigint unsigned not null,
                `time` timestamp default null,
                `comment` varchar(500) not null default '',
                `request_id` bigint not null,
                `invitor_id` bigint unsigned default null,
                `invitor_nick` varchar(50) default null,
                primary key (`request_id`, `group_id`, `user_id`),
                index(`user_id`)
            )charset=utf8mb4, collate=utf8mb4_unicode_ci;""")
            self.start(0, 3*60)
    def judgeTrigger(self, data) -> bool:
        return True
    def addGroupVerication(self, data) -> Union[str, None]:
        try:
            mydb, mycursor = newSqlSession()
            try:
                data['flag'] = int(data['flag'])
            except ValueError:
                pass
            mycursor.execute("""
            insert ignore into `addGroupRecord` (
                `sub_type`, `group_id`, `user_id`, `time`, `comment`, `request_id`
            ) values (
                %s, %s, %s, from_unixtime(%s), %s, %s
            )
            """, (
                data['sub_type'],
                data['group_id'],
                data['user_id'],
                data['time'],
                data['comment'],
                data['flag']
            ))
        except KeyError as e:
            warning("key error in AddGroupRecorder: {}".format(e))
        except mysql.connector.Error as e:
            warning("mysql error in AddGroupRecorder: {}".format(e))
        except BaseException as e:
            warning("exception in AddGroupRecorder: {}".format(e))
        return None
    
    def tick(self,):
        group_system = get_group_system_msg()
        if group_system == None: return
        mydb, mycursor = newSqlSession()

        if group_system['invited_requests'] != None:
            for invq in group_system['invited_requests']:
                mycursor.execute("""
                update `addGroupRecord` set
                `invitor_id` = %s,
                `invitor_nick` = %s where 
                `request_id` = %s""",(
                    invq['invitor_uin'],
                    invq['invitor_nick'],
                    invq['request_id']
                ))
        if group_system['join_requests'] != None:
            for joinq in group_system['join_requests']:
                mycursor.execute("""
                insert ignore into `addGroupRecord` (
                    `group_id`, `user_id`, `comment`, `request_id`, `time`
                ) values (
                    %s, %s, %s, %s, %s
                )
                """, (
                    joinq['group_id'],
                    joinq['requester_uin'],
                    joinq['message'],
                    joinq['request_id'],
                    datetime.datetime.now()
                ))