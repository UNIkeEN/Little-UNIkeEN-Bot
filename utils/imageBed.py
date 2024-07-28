from typing import Dict, Union, Any, List, Tuple, Optional
from utils.basicConfigs import ROOT_PATH, BOT_SELF_QQ
from utils.sqlUtils import newSqlSession
import re, os, time
import uuid
import requests
from PIL import Image
from io import BytesIO
import base64
import hashlib, uuid
import urllib
import urllib.parse
IMGBED_DIR = os.path.join(ROOT_PATH,'data', str(BOT_SELF_QQ), 'imageBed')
os.makedirs(IMGBED_DIR, exist_ok=True)

def getImgFromUrl(cqImgUrl:str)->Optional[Image.Image]:
    """从cq img url中下载图片
    @cqImgUrl: 从gocqhttp获取的图片url
    @return:
        if 获取成功:
            图像
        else:
            None
    """
    try:
        req = requests.get(url=cqImgUrl)
    except:
        parsedUrl = urllib.parse.urlparse(cqImgUrl)
        if parsedUrl.scheme == 'https':
            parsedUrl = list(parsedUrl)
            parsedUrl[0] = 'http'
            cqImgUrl = urllib.parse.urlunparse(parsedUrl)
            req = requests.get(url=cqImgUrl)
        else:
            return None
    if req.status_code == requests.codes.ok:
        try:
            img = Image.open(BytesIO(req.content))
            return img
        except BaseException as e:
            print('verify not ok: {}'.format(e))
            return None
    else:
        return None
    
def createImageBedSql():
    """QQ图片链接容易过期，如果某个图片过期了，但是还存储在通知记录里，就可能导致不好的事情发生。
    因此我们需要实现一个图床，以uuid为key将图片存储在本地一份，当链接过期时启用图床，
    将图片以base64编码发送给服务器"""
    mydb, mycursor = newSqlSession()
    mycursor.execute("""
    create table if not exists `imageBed` (
        `img_name` varchar(100) not null,
        `img_uuid` char(50) not null,
        `md5` char(70) not null,
        `sha256` char(70) not null,
        `create_time` timestamp not null,
        primary key(`img_uuid`)
    );""")

def dumpImageToBed(img: Image.Image)->str:
    uuidStr = str(uuid.uuid4())
    name = uuidStr + '.' + img.format.lower()
    savePath = os.path.join(IMGBED_DIR, name)
    img.save(savePath)
    md5 = hashlib.md5(img.tobytes()).hexdigest()
    sha256 = hashlib.sha256(img.tobytes()).hexdigest()
    mydb, mycursor = newSqlSession()
    mycursor.execute("""replace into `imageBed`
    (`img_name`, `img_uuid`, `md5`, `sha256`, `create_time`) values
    (%s, %s, %s, %s, from_unixtime(%s))""",
    (name, uuidStr, md5, sha256, int(time.time())))
    return uuidStr

def dumpUrlToBed(imgUrl:str)->Optional[str]:
    img = getImgFromUrl(imgUrl)
    if img == None:
        return None
    return dumpImageToBed(img)

def uuidToImgPath(uuid:str)->Optional[str]:
    mydb, mycursor = newSqlSession()
    mycursor.execute("""
    select `img_name` from `imageBed`
    where `img_uuid` = %s""", (uuid, ))
    result = list(mycursor)
    if len(result) == 0:
        return None
    else:
        return os.path.join(IMGBED_DIR, result[0][0])

def uuidToImgBase64(uuid:str)->Optional[str]:
    imgPath = uuidToImgPath(uuid)
    if imgPath == None: return None
    img = Image.open(imgPath)
    imgData = BytesIO()
    img.save(imgData, format=img.format)
    b64img = base64.b64encode(imgData.getvalue()).decode('utf-8')
    return b64img

if __name__ == '__main__':
    mydb, mycursor = newSqlSession()
