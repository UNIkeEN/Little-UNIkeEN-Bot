## 1. 插件简介

| 插件名称 | 父类 | 触发关键词 | 触发权限 | 内容 |
| ---- | ---- | ---- | ---- | ---- |
| GocqWatchDog | WatchDog | `None` | None | go-cqhttp离线报警 |

## 2. 示范样例

当go-cqhttp离线时，`WARNING_ADMIN_ID`收到邮件：

```bash
Little-Unicorn-Bot warning
    warning: QQ Bot offline
```

## 3. 代码分析

主要代码位于 `plugins/gocqWatchDog.py`

```python hl_lines="1 4 5 69 70 73"
# main.py
def eventClassify(json_data: dict)->NoticeType: 
    """事件分类"""
    if json_data['post_type'] == 'meta_event' and json_data['meta_event_type'] == 'heartbeat':
        return NoticeType.GocqHeartBeat
    if json_data['post_type'] == 'message' and json_data['message_type'] == 'group':
        if json_data['group_id'] in APPLY_GROUP_ID:
            return NoticeType.GroupMessage
        else:
            return NoticeType.GroupMessageNoProcessRequired
    if json_data['post_type'] == 'message' and json_data['message_type'] == 'private':
        return NoticeType.PrivateMessage
    if json_data['post_type'] == 'notice' and json_data['notice_type'] == 'notify' and json_data['sub_type'] == "poke":
        if 'group_id' in json_data.keys() and json_data['group_id'] in APPLY_GROUP_ID:
            return NoticeType.GroupPoke
    if json_data['post_type'] == 'notice' and json_data['notice_type'] == 'group_recall':
        return NoticeType.GroupRecall
    if json_data['post_type'] == 'notice' and json_data['notice_type'] == 'group_upload':
        return NoticeType.GroupUpload
    if json_data['post_type'] == 'request' and json_data['request_type'] == 'friend':
        return NoticeType.AddPrivate
    return NoticeType.NoProcessRequired

@app.route('/', methods=["POST"])
def post_data():
    # 获取事件上报
    data = request.get_json()
    # 筛选并处理指定事件
    flag=eventClassify(data)
    # 群消息处理
    if flag==NoticeType.GroupMessage: 
        msg=data['message'].strip()
        for event in GroupPluginList:
            event: StandardPlugin
            try:
                if event.judgeTrigger(msg, data):
                    ret = event.executeEvent(msg, data)
                    if ret != None:
                        return ret
            except TypeError as e:
                warning("type error in main.py: {}\n\n{}".format(e, event))
    elif flag == NoticeType.GroupMessageNoProcessRequired:
        groupMessageRecorder.executeEvent(data['message'], data)
    elif flag == NoticeType.GroupRecall:
        for plugin in [groupMessageRecorder]:
            plugin.recallMessage(data)

    # 私聊消息处理
    elif flag==NoticeType.PrivateMessage:
        # print(data)
        msg=data['message'].strip()
        for event in PrivatePluginList:
            if event.judgeTrigger(msg, data):
                if event.executeEvent(msg, data)!=None:
                    break
    elif flag == NoticeType.GroupUpload:
        for event in [GroupFileRecorder()]:
            event.uploadFile(data)
    # 群内拍一拍回拍
    elif flag==NoticeType.GroupPoke: 
        for p in GroupPokeList:
            if p.judgeTrigger(data):
                if p.pokeMessage(data)!=None:
                    break
            
    # 自动加好友
    elif flag==NoticeType.AddPrivate:
        set_friend_add_request(data['flag'], True)
    elif flag==NoticeType.GocqHeartBeat:
        gocqWatchDog.feed()
    return "OK"

# plugins/gocqWatchDog.py
from utils.standardPlugin import WatchDog
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from utils.basicConfigs import MAIL_USER, MAIL_PASS, WARNING_ADMIN_ID
from typing import List, Tuple, Any, Optional, Dict
def sendEmailTo(msg: str, receivers:List[str])->bool:
    """send msg to receivers"""
    try:
        message = MIMEText(msg)
        message['From'] = Header('Little-Unicorn-Bot', 'utf-8')
        message['To'] = Header('bot root admins', 'utf-8')
        message['Subject'] = Header('Little-Unicorn-Bot warning')
        smtpobj = smtplib.SMTP_SSL('smtp.qq.com',465)
        smtpobj.login(MAIL_USER, MAIL_PASS)
        smtpobj.sendmail(MAIL_USER, receivers, message.as_string())
        smtpobj.quit()
    except BaseException as e:
        return False

class GocqWatchDog(WatchDog):
    def __init__(self, intervalTime:float):
        super().__init__(intervalTime)
    def onHungry(self):
        sendEmailTo('warning: QQ Bot offline', ['%d@qq.com'%u for u in WARNING_ADMIN_ID])
```