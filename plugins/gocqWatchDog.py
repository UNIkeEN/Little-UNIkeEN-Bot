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