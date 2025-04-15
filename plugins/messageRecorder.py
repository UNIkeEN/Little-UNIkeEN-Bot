import threading
import time

import mysql.connector
from pymysql.converters import escape_string

from utils.basicEvent import get_group_list, get_group_msg_history, warning
from utils.sqlUtils import newSqlSession
from utils.standardPlugin import (Any, List, RecallMessageStandardPlugin,
                                  StandardPlugin, Tuple, Union)


def getLatestRecordSeq():
    groupList = [group['group_id'] for group in get_group_list()]
    mydb, mycursor = newSqlSession(autocommit=False)
    result = []
    for group_id in groupList:
        if not isinstance(group_id, int): continue
        mycursor.execute("""
            select max(message_seq) from `messageRecord`
            where group_id = %d"""%group_id)
        latestSeq = list(mycursor)
        if len(latestSeq) == 0:
            latestSeq = None
        else:
            latestSeq = latestSeq[0][0]
        result.append((group_id, latestSeq))
    return result
def getGroupMessageHistory(group_id: int, message_seq: Union[int, None]=None)->list:
    """获取聊天记录
    @group_id: 群号
    @message_seq: 
        if None: 获取最新19条消息记录
        else:    获取包含左开右闭区间(message_seq, latest_seq]的消息记录列表
    @return: 消息记录列表
    """
    time.sleep(1)
    messages = get_group_msg_history(group_id)
    if message_seq == None or len(messages) == 0:
        return messages
    for seq in range(message_seq, messages[-1]['message_seq'], 19):
        messages.append(get_group_msg_history(group_id, seq))
        time.sleep(1)
    return messages

def getGroupMessageThread(latestResultSeq):
    def flatten(messages):
        result = []
        for data in messages:
            if isinstance(data, list):
                result.extend(flatten(data))
            else:
                result.append(data)
        return result
    mydb, mycursor = newSqlSession()
    for group_id, latest_seq in latestResultSeq:
        messages = getGroupMessageHistory(group_id, latest_seq)
        print("get {} messages from group {}".format(len(messages), group_id))
        for data in flatten(messages):
            try:
                if 'card' not in data['sender'].keys():
                    card = data['anonymous']['name']
                else:
                    card = data['sender']['card']
                mycursor.execute("""
                    insert ignore into `messageRecord`
                    (`message_id`, `message_seq`, `time`, `user_id`,
                    `message`, `group_id`, `nickname`, `card`) 
                    values (%d, %d, from_unixtime(%d), %d, '%s', %d, '%s', '%s')"""%(
                        data['message_id'],
                        data['message_seq'],
                        data['time'],
                        data['user_id'],
                        escape_string(data['message']),
                        data['group_id'],
                        escape_string(data['sender']['nickname']),
                        escape_string(card)
                    )
                )
            except mysql.connector.Error as e:
                print(data)
                warning("mysql error in getGroupMessageThread: {}".format(e))
            except KeyError as e:
                print(data)
                warning("key error in getGroupMessageThread: {}".format(e))
            except BaseException as e:
                print(data)
                warning("exception in getGroupMessageThread: {}".format(e))
                # with open("getGroupMessageThreadData.json", 'w') as f:
                #     json.dump(data, f)

class GroupMessageRecorder(StandardPlugin, RecallMessageStandardPlugin):
    def __init__(self) -> None:
        # 首先获取群聊列表，看看数据库是否开了这些表
        mydb, mycursor = newSqlSession()
        mycursor.execute("""
        create table if not exists `messageRecord`(
            `message_id` bigint not null,
            `message_seq` bigint not null,
            `time` timestamp not null,
            `user_id` bigint not null,
            `message` varchar(6000) not null,
            `group_id` bigint not null,
            `nickname` varchar(50) not null,
            `card` varchar(50) not null,
            `recall` bool not null default false,
            primary key (`group_id`, `message_seq`)
        )charset=utf8mb4, collate=utf8mb4_unicode_ci;""")
        # 多线程获取离线期间的聊天记录
        if False:
            try:
                latestResultSeq = getLatestRecordSeq()
                self._getGroupMessageThread = threading.Thread(target=getGroupMessageThread,args=(latestResultSeq,))
                self._getGroupMessageThread.daemon = True
                self._getGroupMessageThread.start()
            except Exception as e:
                pass
    def recallMessage(self, data: Any):
        try:
            mydb, mycursor = newSqlSession()
            mycursor.execute("""
                update `messageRecord` set recall=true where 
                group_id = %d and message_id = %d
            """%(
                data['group_id'], data['message_id']
            ))
        except KeyError as e:
            warning("key error in recall message: {}".format(e))
        except mysql.connector.Error as e:
            warning("mysql error in recall message: {}".format(e))
        except BaseException as e:
            warning("exception in recall message: {}".format(e))
        return None
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return data['message_type']=='group'

    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        try:
            mydb, mycursor = newSqlSession()
            if 'card' not in data['sender'].keys():
                card = data['anonymous']['name']
            else:
                card = data['sender']['card']
                if card == None:
                    card = ''
            backendTime:int = data['time'] # timestamp in second
            '''
            # FIX: backend time error
            systemTime:int = int(time.time())
            if abs(backendTime - systemTime) > 60:
                backendTime = systemTime
            '''
            mycursor.execute("""
                insert ignore into `messageRecord`
                (`message_id`, `message_seq`, `time`, `user_id`,
                `message`, `group_id`, `nickname`, `card`) 
                values (%d, %d, from_unixtime(%d), %d, '%s', %d, '%s', '%s')"""%(
                    data['message_id'],
                    data['message_seq'],
                    backendTime,
                    data['user_id'],
                    escape_string(data['message']),
                    data['group_id'],
                    escape_string(data['sender']['nickname']),
                    escape_string(card)
                )
            )
        except mysql.connector.Error as e:
            warning("mysql error in MessageRecorder: {}".format(e))
        except KeyError as e:
            warning("key error in MessageRecorder: {}".format(e))
        except BaseException as e:
            warning("exception in MessageRecorder: {}".format(e))
        return None

    def getPluginInfo(self) -> dict:
        return {
            'name': 'GroupMessageRecorder',
            'description': '记录群聊消息',
            'commandDescription': '',
            'usePlace': ['group', 'group_recall'],
            'showInHelp': False,                
            'pluginConfigTableNames': ['messageRecord', ],
            'version': '1.0.0',
            'author': 'Unicorn',
        }