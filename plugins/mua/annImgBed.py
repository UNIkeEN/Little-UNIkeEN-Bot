from typing import Dict, Union, Any, List, Tuple, Optional
from utils.basicEvent import getImgFromUrl
from utils.basicConfigs import ROOT_PATH, SAVE_TMP_PATH, sqlConfig
import re, os, time
import uuid
import mysql.connector
from pymysql.converters import escape_string
from PIL import Image
from io import BytesIO
import base64

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
        return os.path.join(ROOT_PATH, ANN_IMGBED_DIR, result[0][0])

def imgUrlToImgBase64(imgUrl:str)->Optional[str]:
    imgPath = imgUrlToImgPath(imgUrl)
    if imgPath == None: return None
    img = Image.open(imgPath)
    imgData = BytesIO()
    img.save(imgData, format=img.format)
    b64img = base64.b64encode(imgData.getvalue()).decode('utf-8')
    return b64img

def urlOrBase64ToImage(imgType:str, imgContent:str)->Optional[Image.Image]:
    if imgType == 'imgurl':
        imgPath = imgUrlToImgPath(imgContent)
        if imgPath != None:
            return Image.open(imgPath)
        else:
            req = requests.get(url=imgContent)
            if req.status_code == requests.codes.ok:
                try:
                    return Image.open(BytesIO(requests.content))
                except:
                    return None
            else:
                return None
    elif imgType == 'imgbase64':
        try:
            return Image.open(BytesIO(base64.decode(imgContent)))
        except:
            return None
    else:
        return None

def dumpMsgToBed(msg:str):
    imgPattern = re.compile(r'\[CQ\:image\,file\=[^\,]+\,subType=\S+\,url\=([^\,]+)\]')
    for url in imgPattern.findall(msg):
        if dumpUrlToBed(url):
            print('dump OK: url =', url)
        else:
            print('dump fail: url =', url)

# if True:
if __name__ == '__main__':
    mydb = mysql.connector.connect(charset='utf8mb4',**sqlConfig)
    mydb.autocommit = True
    mycursor = mydb.cursor()
    mycursor.execute("""
    select `img_url`,`img_name` from `BOT_DATA`.`muaAnnImgbed`
    limit 1""")
    result = list(mycursor)
    if len(result) == 0:
        print('测试失败，图床为空')
    else:
        imgUrl, imgName = result[0]
        picPath = imgUrlToImgPath(imgUrl)
        print('img path:', picPath)
        b64img = imgUrlToImgBase64(imgUrl)
        print(b64img)