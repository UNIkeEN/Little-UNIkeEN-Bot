from utils.standardPlugin import StandardPlugin, RecallMessageStandardPlugin, Union, Tuple, Any, List
from utils.basicEvent import get_group_list, warning, get_group_list, get_group_msg_history
from utils.basicConfigs import sqlConfig
from pymysql.converters import escape_string
import mysql.connector
import threading, time

def getLatestRecordSeq():
    groupList = [group['group_id'] for group in get_group_list()]
    mydb = mysql.connector.connect(charset='utf8mb4',**sqlConfig)
    mycursor = mydb.cursor()
    result = []
    for group_id in groupList:
        if not isinstance(group_id, int): continue
        mycursor.execute("""
            select max(message_seq) from `BOT_DATA`.`messageRecord`
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
    mydb = mysql.connector.connect(charset='utf8mb4',**sqlConfig)
    mydb.autocommit = True
    mycursor = mydb.cursor()
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
                    insert ignore into `BOT_DATA`.`messageRecord`
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
        mydb = mysql.connector.connect(charset='utf8mb4',**sqlConfig)
        mydb.autocommit = True
        mycursor = mydb.cursor()
        mycursor.execute("""
        create database if not exists `BOT_DATA`
        """)
        mycursor.execute("""
        create table if not exists `BOT_DATA`.`messageRecord`(
            `message_id` int not null,
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
        latestResultSeq = getLatestRecordSeq()
        self._getGroupMessageThread = threading.Thread(target=getGroupMessageThread,args=(latestResultSeq,))
        self._getGroupMessageThread.start()
    def recallMessage(self, data: Any):
        try:
            mydb = mysql.connector.connect(charset='utf8mb4',**sqlConfig)
            mydb.autocommit = True
            mycursor = mydb.cursor()
            mycursor.execute("""
                update `BOT_DATA`.`messageRecord` set recall=true where 
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
            mydb = mysql.connector.connect(charset='utf8mb4',**sqlConfig)
            mydb.autocommit = True
            mycursor = mydb.cursor()
            if 'card' not in data['sender'].keys():
                card = data['anonymous']['name']
            else:
                card = data['sender']['card']
            mycursor.execute("""
                insert ignore into `BOT_DATA`.`messageRecord`
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