from PIL import Image, ImageDraw, ImageFont
import random
import requests
import time
import base64
import binascii
import datetime
import hashlib
import json
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from io import BytesIO
import mysql.connector
from typing import Union, Any
from utils.basicEvent import *
from utils.basicConfigs import *
from utils.standardPlugin import StandardPlugin
import re

class IcolaUserBind(StandardPlugin): 
    def __init__(self) -> None:
        self.pattern1 = re.compile(r'^(\-icoke|\-icola)$')
        self.pattern2 = re.compile(r'^(\-icoke|\-icola)\s+unbind$')
        self.pattern3 = re.compile(r'^(\-icoke|\-icola)\s+bind\s+(\S+)$')
        try:
            mydb = mysql.connector.connect(**sqlConfig)
            mycursor = mydb.cursor()
            mycursor.execute("""create table if not exists `BOT_DATA`.`icola` (
                `qq` bigint not null,
                `userInfo` char(128) not null,
                primary key (`qq`)
            );""")
        except BaseException as e:
            warning('icola 无法连接至数据库, error: {}'.format(e))
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return startswith_in(msg, ['-icola', '-icoke'])
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        if self.pattern1.match(msg) != None:
            send(target,"每日雪碧操作指引：\n1. 若未绑定授权码，请先前往 https://icola2023.github.io/icola2023/ 获取授权码，然后发送命令-icola bind XXXXXXXXX 进行绑定。\n2. 绑定授权码后，每日使用小马【签到】时将同步领取当日免费麦当劳雪碧兑换券。\n3. 打开麦当劳APP或小程序，即可看到兑换券。", data['message_type'])
        elif self.pattern2.match(msg) != None:
            if unbind_icola(data['user_id']):
                send(target,"[CQ:reply,id=%d]解绑成功"%data['message_id'], data['message_type'])
            else:
                send(target,"[CQ:reply,id=%d]解绑失败"%data['message_id'], data['message_type'])
        elif self.pattern3.match(msg) != None:
            _, userCode = self.pattern3.findall(msg)[0]
            if not isbase64(userCode) or len(userCode) > 128:
                send(target,'格式错误，请检查授权码符合格式', data['message_type'])
            else:
                if edit_bind_icola(data['user_id'], userCode):
                    send(target,"[CQ:reply,id=%d]绑定成功"%data['message_id'], data['message_type'])
                else:
                    send(target,"[CQ:reply,id=%d]绑定失败"%data['message_id'], data['message_type'])
        else:
            send(target,"[CQ:reply,id=%d]指令解析失败，请发送-icola获取帮助"%data['message_id'], data['message_type'])

        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'icolaBind',
            'description': '麦当劳每日雪碧券绑定',
            'commandDescription': '-icola bind [授权码]',
            'usePlace': ['group', 'private'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Teruteru',
        }

def edit_bind_icola(qq_id: Union[int, str], code: str)->bool:
        if isinstance(qq_id, str):
            qq_id = int(qq_id)
        try:
            mydb = mysql.connector.connect(**sqlConfig)
            mycursor = mydb.cursor()
            mycursor.execute("replace into `BOT_DATA`.`icola` values (%d, '%s')"%(qq_id, escape_string(code)))
            mydb.commit()
            return True
        except BaseException as e:
            warning("error in icola, error: {}".format(e))
            return False
def unbind_icola(qq_id: Union[int, str])->bool:
    if isinstance(qq_id, str):
        qq_id = int(qq_id)
    try:
        mydb = mysql.connector.connect(**sqlConfig)
        mycursor = mydb.cursor()
        mycursor.execute("delete from `BOT_DATA`.`icola` where qq=%d"%(qq_id))
        mydb.commit()
        return True
    except BaseException as e:
        warning("error in icola, error: {}".format(e))
        return False

#获取雪碧
def getTea(qq_id) -> Tuple[bool, str]:
    if isinstance(qq_id, str):
        qq_id = int(qq_id)
    try:
        mydb = mysql.connector.connect(**sqlConfig)
        mycursor = mydb.cursor()
        mycursor.execute("select userInfo from `BOT_DATA`.`icola` where qq=%d"%(qq_id))
        codes = list(mycursor)
        if len(codes) == 0:
            return False, "查询失败"
        else:
            encdata = codes[0][0]
    except BaseException as e:
        warning("error in getCoke, error: {}".format(e))
        return False, "数据库错误"
    try:
        key = b'cola2023cola2023'
        aes = AES.new(key,AES.MODE_ECB)
        userInfoText = aes.decrypt(base64.b64decode(encdata))
        userInfoText = unpad(userInfoText, AES.block_size, 'pkcs7')
        print(userInfoText)
        userInfoJson = json.loads(userInfoText)
        query1 = "app=0&channel=5842&mobile="+userInfoJson['phone']+"&platform=0&snsid="+userInfoJson['snsid']+"&cityid=635";
        query2 = "&smscode=&app=0&channel=5842&platform=0&cityid=635&mobile="+userInfoJson['phone']+"&snsid="+userInfoJson['snsid'];
    except Exception as e:
        print(e)
        return False, "获取用户信息失败，请尝试重新绑定！"
    try:
        ret1 = requests.get("https://co.moji.com/api/cola2023/userCoupon?" + query1,timeout=5,verify=False)
        if ret1.status_code != requests.codes.ok:
            return False, f"请求失败：{ret1.status_code}"
        if ret1.json()["code"] != 0:
            msg = ret1.json()["msg"]
            return False, f"{msg}"
        if ret1.json()["data"]["coupon"] == "":
            ret2 = requests.get("https://co.moji.com/api/cola2023/raffle?" + query2,timeout=5,verify=False)
            if ret2.status_code != requests.codes.ok:
                return False, f"请求失败：{ret2.status_code}"
            if ret2.json()["code"] != 0:
                msg = ret2.json()["msg"]
                return False, f"{msg}"
            if ret2.json()["data"]["coupon"] == "":
                return False, "领取失败，原因未知！"
        return True, "获得今日雪碧一份！"
    except Exception as e:
        return False, "访问网页失败"

def isbase64(text:str)->bool:
    try:
        base64.b64decode(text)
    except binascii.Error:
        return False
    return True