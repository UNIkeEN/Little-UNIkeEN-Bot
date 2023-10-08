import requests
from utils.standard_plugin import GroupUploadStandardPlugin, Union, Tuple, Any, List
from utils.basic_event import get_group_list, warning
from utils.basic_event import get_group_file_system_info, get_group_files_by_folder, get_group_root_files, get_group_file_url
from utils.basic_configs import sqlConfig
from utils.sql_utils import newSqlSession
import mysql.connector
"""
# 筛选file_id:
select group_id, file_id, file_name, busid, file_size, (file_bin is not null) from BOT_DATA_%d.fileRecord where ...;
# 导出文件
select file_bin from BOT_DATA_%d.fileRecord where group_id = %s and file_id = %s into dumpfile '/var/lib/mysql-files/...';

eg:
mysql>      select file_bin from BOT_DATA_%d.fileRecord where group_id = 604329164 and file_id = '/cf1f95db-5abe-44c3-bba6-29e5b702052c' into dumpfile '/var/lib/mysql-files/tmp.pdf';
bash>       sudo mv /var/lib/mysql-files/tmp.pdf /tmp/tmp.pdf
bash>       sudo chmod 777 /tmp/tmp.pdf
powershell> scp ubuntu@xxx.xxx:/tmp/tmp.pdf ~/Desktop/
"""

def createSqlFileTable():
    """建表"""
    mydb, mycursor = newSqlSession()
    mycursor.execute("""
    create table if not exists `fileRecord`(
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
    def uploadFile(self, data)->Union[str, None]:
        file = data['file']
        mydb, mycursor = newSqlSession()
        mycursor = mydb.cursor()
        try:
            mycursor.execute("""
            insert into `fileRecord` (
                group_id, file_id, file_name, busid, file_size, upload_time,
                uploader,  file_url
            ) values (
                %s,       %s,        %s,       %s,   %s, from_unixtime(%s), 
                %s,        %s
            )""", (
                data['group_id'],
                file['id'],
                file['name'],
                file['busid'],
                file['size'],
                data['time'],
                data['user_id'],
                file['url'],
            ))
            if file['size'] < 1024* 1024* 100: # 100MB
                req = requests.get(file['url'])
                if req.status_code != requests.codes.ok:
                    warning("tencent file API failed in file recorder")
                    return "OK"
                mycursor.execute("""update `fileRecord` set `file_bin`= %s
                    where group_id = %s and file_id = %s and busid = %s""",(
                    req.content, data['group_id'], file['id'], file['busid']
                ))
        except KeyError as e:
            warning("key error in file recorder: {}".format(e))
        except mysql.connector.Error as e:
            warning("mysql error in file recorder: {}".format(e))
        except BaseException as e:
            warning("base exception in file recorder: {}".format(e))
        finally:
            return "OK"