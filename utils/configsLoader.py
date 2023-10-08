from .basic_configs import APPLY_GROUP_ID
from .sql_utils import newSqlSession
from typing import Optional, List, Tuple

def createApplyGroupsSql():
    mydb, mycursor = newSqlSession()
    mycursor.execute("""
    create table if not exists `applyGroupId`(
        `group_id` bigint unsigned not null comment '群号',
        `description` varchar(100) default null comment '群标识',
        primary key (`group_id`)
    )charset=utf8mb4, collate=utf8mb4_unicode_ci;""")

def loadApplyGroupId():
    mydb, mycursor = newSqlSession()
    mycursor.execute("""
    select `group_id` from `applyGroupId`
    """)
    result = [groupId for groupId, in list(mycursor)]
    APPLY_GROUP_ID.extend(result)

def getApplyGroups()->List[Tuple[int, str]]:
    mydb, mycursor = newSqlSession()
    mycursor.execute("""
    select `group_id`, `description` from `applyGroupId`
    """)
    return list(mycursor)
    
def addGroupToApplyId(groupId:int, description:Optional[str]=None):
    mydb, mycursor = newSqlSession()
    mycursor.execute("""replace into `applyGroupId`
    (`group_id`, `description`) values (%s, %s)
    """, (groupId, description))
    groups = set(APPLY_GROUP_ID)
    groups.add(groupId)
    APPLY_GROUP_ID.clear()
    APPLY_GROUP_ID.extend(groups)

def delGroupFromApplyId(groupId:int):
    mydb, mycursor = newSqlSession()
    mycursor.execute("""delete from `applyGroupId`
    where `group_id` = %s""", (groupId, ))
    groups = set(APPLY_GROUP_ID)
    groups.discard(groupId)
    APPLY_GROUP_ID.clear()
    APPLY_GROUP_ID.extend(groups)