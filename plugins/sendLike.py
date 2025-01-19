from utils.standardPlugin import StandardPlugin
from typing import List, Any, Dict, Optional, Union, Set, Tuple
from utils.basicEvent import send, warning, send_like
from utils.sqlUtils import newSqlSession
from utils.accountOperation import get_user_coins, update_user_coins
from utils.sqlUtils import newSqlSession
from datetime import date

def createSendlikeSql():
    mydb, mycursor = newSqlSession()
    mycursor.execute("""
        create table if not exists `sendLike` (
            `id` bigint not null,
            `signDate` date not null,
            `likeCount` int,
            primary key (`id`, `signDate`)
        );""")

def querySentLikeCount(qq:int, day: date)->int:
    mydb, mycursor = newSqlSession()
    mycursor.execute("""
    select `likeCount` from `sendLike` where
    `id` = %s and `signDate` = %s""", (qq, day))
    result = list(mycursor)
    if len(result) == 0:
        return 0
    return result[0][0]

def recordSentLike(qq: int, day: date, count: int)->None:
    mydb, mycursor = newSqlSession()
    mycursor.execute("""insert ignore into `sendLike`
                     (`id`, `signDate`, `likeCount`)
                     values (%s, %s, %s)""", (qq, day, count))

class SendLike(StandardPlugin):
    def __init__(self):
        createSendlikeSql()
        
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return (msg in ['赞下'])
    
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        qq = data['user_id']
        today = date.today()
        if querySentLikeCount(qq, today) > 0:
            send(target, '[CQ:reply,id=%d]今日已赞，请明日再来'%data['message_id'], data['message_type'])
        else:
            coins = get_user_coins(qq, False)
            likeCount = 10 if coins >= 100_00 else coins // 10_00
            if likeCount > 0:
                costs = -likeCount * 10_00
                update_user_coins(qq, costs, '资料卡点赞', False)
                send_like(qq, likeCount)
                recordSentLike(qq, today, likeCount)
                send(target, '[CQ:reply,id=%d]已送出%d个赞，请查收'%(data['message_id'], likeCount), data['message_type'])
            else:
                send(target, '[CQ:reply,id=%d]coins已不足10，请签到获取'%data['message_id'], data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'SendLike',
            'description': '资料卡点赞（10coins/赞）',
            'commandDescription': '赞下',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': ['sendLike'],
            'version': '1.0.0',
            'author': 'Unicorn',
        }