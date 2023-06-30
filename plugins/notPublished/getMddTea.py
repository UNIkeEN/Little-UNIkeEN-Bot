from PIL import Image, ImageDraw, ImageFont
import random
import requests
import time
import datetime
import hashlib
from io import BytesIO
import mysql.connector
from typing import Union, Any
from utils.basicEvent import *
from utils.basicConfigs import *
from utils.standardPlugin import StandardPlugin

class IcokeUserBind(StandardPlugin): 
    def __init__(self) -> None:
        try:
            mydb = mysql.connector.connect(**sqlConfig)
            mycursor = mydb.cursor()
            mycursor.execute("""create table if not exists `BOT_DATA`.`icoke` (
                `qq` bigint not null,
                `userValue` char(128) not null,
                primary key (`qq`)
            );""")
        except BaseException as e:
            warning('icoke 无法连接至数据库, error: {}'.format(e))
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return startswith_in(msg, ['-icoke'])
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        if (msg.strip() == '-icoke'):
            send(target,"每日柠檬红茶饮料操作指引：\n1. 若未绑定授权码，请先前往 http://10.119.4.90:443/icoke.html 获取授权码，然后发送命令-icoke bind XXXXXXXXX 进行绑定。\n2. 绑定授权码后，每日使用小马【签到】时将同步领取当日免费麦当劳中杯【阳光】柠檬红茶味饮料券。\n3. 打开麦当劳APP或小程序，即可看到优惠券。", data['message_type'])
            # send(target,f'[CQ:image,file=files:///{canvasPicPath}]', data['message_type'])
            return "OK"
        if (msg.strip() == '-icoke unbind'):
            if unbind_icoke(data['user_id']):
                send(target,"解绑成功", data['message_type'])
            else:
                send(target,"解绑失败", data['message_type'])
            return "OK"
        if (startswith_in(msg, ['-icoke bind '])):
            msg=msg.replace('-icoke bind ','',1).strip()
            if len(msg) != 32:
                send(target,'格式错误，请检查授权码符合格式', data['message_type'])
            else:
                if edit_bind_icoke(data['user_id'], msg):
                    send(target,"绑定成功", data['message_type'])
                else:
                    send(target,"绑定失败", data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'IcokeBind',
            'description': '麦当劳每日饮料券绑定',
            'commandDescription': '-icoke bind [授权码]',
            'usePlace': ['group', 'private'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Teruteru',
        }

def edit_bind_icoke(qq_id: Union[int, str], code: str)->bool:
        if isinstance(qq_id, str):
            qq_id = int(qq_id)
        try:
            mydb = mysql.connector.connect(**sqlConfig)
            mycursor = mydb.cursor()
            mycursor.execute("replace into `BOT_DATA`.`icoke` values (%d, '%s')"%(qq_id, escape_string(code)))
            mydb.commit()
            return True
        except BaseException as e:
            warning("error in icoke, error: {}".format(e))
            return False
def unbind_icoke(qq_id: Union[int, str])->bool:
    if isinstance(qq_id, str):
        qq_id = int(qq_id)
    try:
        mydb = mysql.connector.connect(**sqlConfig)
        mycursor = mydb.cursor()
        mycursor.execute("delete from `BOT_DATA`.`icoke` where qq=%d"%(qq_id))
        mydb.commit()
        return True
    except BaseException as e:
        warning("error in icoke, error: {}".format(e))
        return False

#获取柠檬红茶
def getTea(qq_id) -> Tuple[bool, str]:
    code = 0
    if isinstance(qq_id, str):
        qq_id = int(qq_id)
    try:
        mydb = mysql.connector.connect(**sqlConfig)
        mycursor = mydb.cursor()
        mycursor.execute("select userValue from `BOT_DATA`.`icoke` where qq=%d"%(qq_id))
        codes = list(mycursor)
        if len(codes) == 0:
            return False, "查询失败"
        else:
            code = codes[0][0]
    except BaseException as e:
        warning("error in getCoke, error: {}".format(e))
        return False, "数据库错误"

    t = int(time.time()*1000)
    text = "timestamp="+str(t)+"&userValue="+code+"7Wf019BZQPLH5EVM9tmqU0adxmZ5mBou"
    md5 = hashlib.md5()
    md5.update(text.encode())
    sign = md5.hexdigest().upper()
    try:
        ret2 = requests.post("https://coke-iu.icoke.cn/zex-cola-iu/mc/coupon/receive",json={"userValue":code, "timestamp":str(t), "sign":sign},timeout=5,verify=False)
        if ret2.status_code != requests.codes.ok:
            return False, f"请求失败：{ret2.status_code}"
        if ret2.json()["isSuccess"] != True:
            msg = ret2.json()["msg"]
            return False, f"{msg}"
        return True, "获得柠檬红茶饮料一份！"
    except BaseException as e:
        return False, "访问网页失败"