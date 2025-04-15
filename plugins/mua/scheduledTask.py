# import schedule
import threading
import time

'''
schedule.every(37).minutes.do(job) # 每10秒执行一次
def createMuaAScheduleSql():
    mydb, mycursor = newSqlSession()
    mycursor.execute("""
    create table if not exists `muaSchedule` (
        `group_id` bigint unsigned not null comment 'QQ群号',
        `interval` int unsigned not null default 0 comment '周期数',
        `mute_from` char(10) not null comment '静音开始时间段',
        `mute_to` char(10) not null comment '静音结束时间段',
        primary key(`user_id`, `token_description`)
    )""")

class MuaScheduledAnnouncement(StandardPlugin):
    def __init__(self):
        self.triggerPattern1 = re.compile(r'^\-mcbsched\s+every\s+(\d+)\s+mins$')
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg.startswith('-mcbsched')
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        userId = data['user_id']
        if self.triggerPattern.match(msg) != None:
             = self.triggerPattern1.findall(msg)[0]
            empowerTarget = int(empowerTarget)
            succ, result = makeEmpower(userId, empowerTarget, muaId)
            send(target, '[CQ:reply,id=%d]%s'%(data['message_id'], result), data['message_type'])
        else:
            send(target, '[CQ:reply,id=%d]指令解析错误，指令格式为“-muaempower [MUAID] [用户QQ或at用户]”，可以输入“-muaempower TEST 1234”或者“-muaempower TEST @用户1234”'%data['message_id'], data['message_type'])
        return 'OK'
    def getPluginInfo(self)->Any:
        return {
            'name': 'MuaTokenEmpower',
            'description': '授权MUA ID',
            'commandDescription': '-muaempower [MUAID] [用户QQ或at用户]',
            'usePlace': ['group', 'private'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }

def scheduleRunPending() -> None:
    while True:
        schedule.run_pending() # 运行所有可运行的任务

threading.Thread(target=scheduleRunPending)
'''