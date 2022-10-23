import requests
from utils.standardPlugin import GroupUploadStandardPlugin, Union, Tuple, Any, List
from utils.basicEvent import get_group_list, warning
from utils.basicEvent import get_group_file_system_info, get_group_files_by_folder, get_group_root_files, get_group_file_url
from utils.basicConfigs import sqlConfig
from pymysql.converters import escape_string
import pymysql, mysql.connector
import threading, time

class QqGroupFile():
    """QQ群文件类型, 对标go-cqhttp的File结构体"""
    def __init__(self) -> None:
        pass

def createSqlFileTable():
    """建表"""
    mydb = mysql.connector.connect(charset='utf8mb4',**sqlConfig)
    mydb.autocommit = True
    mycursor = mydb.cursor()
    mycursor.execute("""
    create table if not exists `BOT_DATA`.`fileRecord`(
        `group_id` bigint not null,
        `file_id`  char(64) not null,
        `file_name` varchar(500) not null default '',
        `busid` int not null,
        `file_size` bigint unsigned not null default 0,
        `upload_time` timestamp not null,
        `uploader` bigint not null,
        `file_url` varchar(300) default null,
        `file_bin` longblob default null,
        primary key (`group_id`, `file_id`, `busid`)
    )charset=utf8mb4, collate=utf8mb4_unicode_ci;
    """)
class GroupFileRecorder(GroupUploadStandardPlugin):
    def __init__(self) -> None:
        createSqlFileTable()
        # select group_id, file_id, file_name, busid, file_size, (file_bin is null) from BOT_DATA.fileRecord;
    def uploadFile(self, data)->Union[str, None]:
        file = data['file']
        mydb = pymysql.connect(charset='utf8mb4',**sqlConfig)
        mydb.autocommit(True)
        mycursor = mydb.cursor()
        try:
            mycursor.execute("""
            insert into `BOT_DATA`.`fileRecord` (
                group_id, file_id, file_name, busid, file_size, upload_time,
                uploader,  file_url
            ) values (
                %s,       %s,        %s,       %s,   %s, from_unixtime(%s), 
                %s,        %s
            )""", (
                data['group_id'],
                escape_string(file['id']),
                escape_string(file['name']),
                file['busid'],
                file['size'],
                data['time'],
                data['user_id'],
                escape_string(file['url']),
            ))
            if file['size'] < 1024* 1024* 100: # 100MB
                req = requests.get(file['url'])
                if req.status_code != requests.codes.ok:
                    warning("tencent file API failed in file recorder")
                    return "OK"
                mycursor.execute("""update `BOT_DATA`.`fileRecord` set `file_bin`= %s
                    where group_id = %s and file_id = %s and busid = %s""",(
                    req.content, data['group_id'], escape_string(file['id']), file['busid']
                ))
        except KeyError as e:
            warning("key error in file recorder: {}".format(e))
        except pymysql.Error as e:
            warning("mysql error in file recorder: {}".format(e))
        except BaseException as e:
            warning("base exception in file recorder: {}".format(e))
        finally:
            return "OK"