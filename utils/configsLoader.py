from .basicConfigs import sqlConfig, APPLY_GROUP_ID
import mysql.connector
from typing import Optional, List, Tuple

def createApplyGroupsSql():
    mydb = mysql.connector.connect(charset='utf8mb4',**sqlConfig)
    mydb.autocommit = True
    mycursor = mydb.cursor()
    mycursor.execute("""
    create table if not exists `BOT_DATA`.`applyGroupId`(
        `group_id` bigint unsigned not null comment '群号',
        `description` varchar(100) default null comment '群标识',
        primary key (`group_id`)
    )charset=utf8mb4, collate=utf8mb4_unicode_ci;""")

def loadApplyGroupId():
    mydb = mysql.connector.connect(charset='utf8mb4',**sqlConfig)
    mydb.autocommit = True
    mycursor = mydb.cursor()
    mycursor.execute("""
    select `group_id` from `BOT_DATA`.`applyGroupId`
    """)
    result = [groupId for groupId, in list(mycursor)]
    APPLY_GROUP_ID.extend(result)

def getApplyGroups()->List[Tuple[int, str]]:
    mydb = mysql.connector.connect(charset='utf8mb4',**sqlConfig)
    mydb.autocommit = True
    mycursor = mydb.cursor()
    mycursor.execute("""
    select `group_id`, `description` from `BOT_DATA`.`applyGroupId`
    """)
    return list(mycursor)
    
def addGroupToApplyId(groupId:int, description:Optional[str]=None):
    mydb = mysql.connector.connect(charset='utf8mb4',**sqlConfig)
    mydb.autocommit = True
    mycursor = mydb.cursor()
    mycursor.execute("""replace into `BOT_DATA`.`applyGroupId`
    (`group_id`, `description`) values (%s, %s)
    """, (groupId, description))
    groups = set(APPLY_GROUP_ID)
    groups.add(groupId)
    APPLY_GROUP_ID.clear()
    APPLY_GROUP_ID.extend(groups)

def delGroupFromApplyId(groupId:int):
    mydb = mysql.connector.connect(charset='utf8mb4',**sqlConfig)
    mydb.autocommit = True
    mycursor = mydb.cursor()
    mycursor.execute("""delete from `BOT_DATA`.`applyGroupId`
    where `group_id` = %s""", (groupId, ))
    groups = set(APPLY_GROUP_ID)
    groups.discard(groupId)
    APPLY_GROUP_ID.clear()
    APPLY_GROUP_ID.extend(groups)