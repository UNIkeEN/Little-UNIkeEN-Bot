from typing import Dict, Union, Any, List, Tuple, Optional
from utils.basicEvent import send, warning, getImgFromUrl
from utils.standardPlugin import StandardPlugin
from utils.basicConfigs import ROOT_PATH, SAVE_TMP_PATH, sqlConfig
import re, os, time
import uuid
import mysql.connector
from pymysql.converters import escape_string

ANN_IMGBED_DIR = 'data/annImgBed'
os.makedirs(os.path.join(ROOT_PATH, ANN_IMGBED_DIR), exist_ok=True)

def createAnnImgBedSql():
    mydb = mysql.connector.connect(**sqlConfig)
    mydb.autocommit = True
    mycursor = mydb.cursor()
    mycursor.execute("""
    create table if not exists `BOT_DATA`.`muaAnnImgbed` (
        `img_name` varchar(100) not null,
        `img_url` varchar(300) not null,
        `create_time` timestamp not null,
        primary key(`img_url`)
    );""")

def dumpUrlToBed(imgUrl:str)->bool:
    img = getImgFromUrl(imgUrl)
    print('img =', img)
    if img == None:
        return False
    name = str(uuid.uuid4()) + '.' + img.format.lower()
    savePath = os.path.join(ROOT_PATH, ANN_IMGBED_DIR, name)
    img.save(savePath)
    mydb = mysql.connector.connect(charset='utf8mb4',**sqlConfig)
    mydb.autocommit = True
    mycursor = mydb.cursor()
    mycursor.execute("""replace into `BOT_DATA`.`muaAnnImgbed`
    (`img_name`, `img_url`, `create_time`) values
    (%s, %s, from_unixtime(%s))""",
    (name, imgUrl, int(time.time())))
    return True

def imgUrlToImgPath(imgUrl:str)->Optional[str]:
    mydb = mysql.connector.connect(charset='utf8mb4',**sqlConfig)
    mydb.autocommit = True
    mycursor = mydb.cursor()
    mycursor.execute("""
    select `img_name` from `BOT_DATA`.`muaAnnImgbed`
    where `img_url` = %s""", (imgUrl, ))
    result = list(mycursor)
    if len(result) == 0:
        return None
    else:
        return os.path.join(ROOT_PATH, SAVE_TMP_PATH, result[0][0])

def dumpMsgToBed(msg:str):
    imgPattern = re.compile(r'\[CQ\:image\,file\=[^\,]+\,subType=\S+\,url\=([^\,]+)\]')
    for url in imgPattern.findall(msg):
        print('dump OK: url =', url)
        dumpUrlToBed(url)
    