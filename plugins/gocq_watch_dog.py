from utils.standard_plugin import WatchDog
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from utils.basic_configs import MAIL_USER, MAIL_PASS, WARNING_ADMIN_ID
from typing import List, Tuple, Any, Optional, Dict


def send_email_to(msg: str, receivers: List[str]) -> bool:
    """send msg to receivers"""
    try:
        message = MIMEText(msg)
        message['From'] = Header('Little-Unicorn-Bot', 'utf-8')
        message['To'] = Header('bot root admins', 'utf-8')
        message['Subject'] = Header('Little-Unicorn-Bot warning')
        smtpobj = smtplib.SMTP_SSL('smtp.qq.com', 465)
        smtpobj.login(MAIL_USER, MAIL_PASS)
        smtpobj.sendmail(MAIL_USER, receivers, message.as_string())
        smtpobj.quit()
    except BaseException as e:
        return False


class GocqWatchDog(WatchDog):
    def __init__(self, intervalTime: float):
        super().__init__(intervalTime)

    def on_hungry(self):
        send_email_to('warning: QQ Bot offline', ['%d@qq.com' % u for u in WARNING_ADMIN_ID])
