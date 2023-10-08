from .basic_configs import APPLY_GROUP_ID
from .sql_utils import new_sql_session
from typing import Optional, List, Tuple


def create_apply_groups_sql():
    mydb, mycursor = new_sql_session()
    mycursor.execute("""
    create table if not exists `applyGroupId`(
        `group_id` bigint unsigned not null comment '群号',
        `description` varchar(100) default null comment '群标识',
        primary key (`group_id`)
    )charset=utf8mb4, collate=utf8mb4_unicode_ci;""")


def load_apply_group_id():
    mydb, mycursor = new_sql_session()
    mycursor.execute("""
    select `group_id` from `applyGroupId`
    """)
    result = [groupId for groupId, in list(mycursor)]
    APPLY_GROUP_ID.extend(result)


def get_apply_groups() -> List[Tuple[int, str]]:
    mydb, mycursor = new_sql_session()
    mycursor.execute("""
    select `group_id`, `description` from `applyGroupId`
    """)
    return list(mycursor)


def add_group_to_apply_id(groupId: int, description: Optional[str] = None):
    mydb, mycursor = new_sql_session()
    mycursor.execute("""replace into `applyGroupId`
    (`group_id`, `description`) values (%s, %s)
    """, (groupId, description))
    groups = set(APPLY_GROUP_ID)
    groups.add(groupId)
    APPLY_GROUP_ID.clear()
    APPLY_GROUP_ID.extend(groups)


def del_group_from_apply_id(groupId: int):
    mydb, mycursor = new_sql_session()
    mycursor.execute("""delete from `applyGroupId`
    where `group_id` = %s""", (groupId,))
    groups = set(APPLY_GROUP_ID)
    groups.discard(groupId)
    APPLY_GROUP_ID.clear()
    APPLY_GROUP_ID.extend(groups)
