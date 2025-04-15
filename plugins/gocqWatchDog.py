import smtplib
from email.header import Header
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Tuple

from utils.basicConfigs import WARNING_ADMIN_ID
from utils.standardPlugin import WatchDog


def sendEmailTo(msg: str, receivers:List[str], mail_user:str, mail_pass:str)->bool:
    """send msg to receivers"""
    try:
        message = MIMEText(msg)
        message['From'] = Header('Little-Unicorn-Bot', 'utf-8')
        message['To'] = Header('bot root admins', 'utf-8')
        message['Subject'] = Header('Little-Unicorn-Bot warning')
        smtpobj = smtplib.SMTP_SSL('smtp.qq.com',465)
        smtpobj.login(mail_user, mail_pass)
        smtpobj.sendmail(mail_user, receivers, message.as_string())
        smtpobj.quit()
    except BaseException as e:
        return False

class GocqWatchDog(WatchDog):
    def __init__(self, intervalTime:float, mail_user:str, mail_pass:str):
        super().__init__(intervalTime)
        self.mail_user = mail_user
        self.mail_pass = mail_pass
        
    def onHungry(self):
        print("gocq watch dog is hungry, send mails...")
        sendEmailTo('warning: QQ Bot offline', ['%d@qq.com'%u for u in WARNING_ADMIN_ID],
                    self.mail_user, self.mail_pass)
        