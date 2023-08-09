import mysql.connector
from utils.standardPlugin import StandardPlugin
from typing import Optional, List, Dict, Any, Union
from utils.basicConfigs import ROOT_ADMIN_ID, sqlConfig
from utils.basicEvent import send, warning
import re
import datetime

class ClearRecord(StandardPlugin):
    def __init__(self):
        mydb = mysql.connector.connect(**sqlConfig)
        mycursor = mydb.cursor()
        mydb.autocommit = True
        mycursor.execute("""
        create table if not exists `BOT_DATA`.`clearChatLog`(
            `group_id` bigint unsigned not null,
            `user_id` bigint unsigned not null,
            `message_seq` bigint not null,
            `last_operate_time` timestamp not null,
            primary key(`group_id`, `user_id`)
        );""")
    def judgeTrigger(self, msg:str, data:Any)->bool:
        return msg == '-actclear' and data['message_type']=='group'
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id']
        mydb = mysql.connector.connect(**sqlConfig)
        mycursor = mydb.cursor()
        mydb.autocommit = True
        # mycursor.execute("select count(*) from `BOT_DATA`.`messageRecord` where user_id = %d and group_id = %d"%(
        #     data['user_id'], data['group_id']))
        # ignore_count = list(mycursor)[0][0]
        mycursor.execute("select last_operate_time from `BOT_DATA`.`clearChatLog` where user_id = %d and group_id = %d"%(
            data['user_id'], data['group_id']))
        result = list(mycursor)
        permitChange = False
        if len(result) == 0: 
            permitChange = True
        elif result[0][0] - datetime.datetime.fromtimestamp(data['time']) > datetime.timedelta(days=60):
            permitChange = True
        if permitChange:
            mycursor.execute("""replace into `BOT_DATA`.`clearChatLog` values
            (%d, %d, %d, from_unixtime(%d))"""%(data['group_id'], data['user_id'], data['message_seq'], data['time']))
            send(target, '[CQ:reply,id=%d]OK'%data['message_id'])
        else:
            send(target, '[CQ:reply,id=%d]同群内，两次修改须间隔60天以上'%data['message_id'])
        return 'OK'
    def getPluginInfo(self, )->Any:
        return {
            'name': 'ClearRecord',
            'description': '清除个人-actrank和-myact的信息（两次修改须间隔60天以上）',
            'commandDescription': '-actclear',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': ['clearChatLog'],
            'version': '1.0.0',
            'author': 'Unicorn',
        }

class RestoreRecord(StandardPlugin):
    def __init__(self):
        self.cmdStyle = re.compile(r'^-actrestore\s*\[CQ:at,qq=(\d+)\]$')
        
    def judgeTrigger(self, msg:str, data:Any)->bool:
        return self.cmdStyle.match(msg) != None and data['message_type']=='group'

    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id']
        if data['user_id'] not in ROOT_ADMIN_ID:
            send(target, '[CQ:reply,id=%d]无权限，请联系bot管理员'%data['message_id'])
        else:
            mydb = mysql.connector.connect(**sqlConfig)
            mycursor = mydb.cursor()
            mydb.autocommit = True
            target_id = int(self.cmdStyle.findall(msg)[0])
            mycursor.execute("""delete from `BOT_DATA`.`clearChatLog` where
            group_id = %d and user_id = %d"""%(data['group_id'], target_id))
            send(target, '[CQ:reply,id=%d]OK'%data['message_id'])
        return 'OK'

    def getPluginInfo(self, )->Any:
        return {
            'name': 'RestoreRecord',
            'description': '恢复指定成员-actrank和-myact的信息[🔒]',
            'commandDescription': '-actrestore @{...}',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': ['clearChatLog'],
            'version': '1.0.0',
            'author': 'Unicorn',
        }