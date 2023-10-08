from typing import Dict, Union, Any, List, Tuple, Optional
from utils.basic_event import get_img_from_url
from utils.basic_configs import ROOT_PATH
from utils.sql_utils import new_sql_session
import re, os, time
import uuid
import requests
from PIL import Image
from io import BytesIO
import base64
from icecream import ic

ANN_IMGBED_DIR = 'data/annImgBed'
os.makedirs(os.path.join(ROOT_PATH, ANN_IMGBED_DIR), exist_ok=True)


def create_ann_img_bed_sql():
    """QQ图片链接容易过期，如果某个图片过期了，但是还存储在通知记录里，就可能导致不好的事情发生。
    因此我们需要实现一个图床，以url为key将图片存储在本地一份，当链接过期时启用图床，
    将图片以base64编码发送给服务器"""
    mydb, mycursor = new_sql_session()
    mycursor.execute("""
    create table if not exists `muaAnnImgbed` (
        `img_name` varchar(100) not null,
        `img_url` varchar(300) not null,
        `create_time` timestamp not null,
        primary key(`img_url`)
    );""")


def dump_url_to_bed(imgUrl: str) -> bool:
    img = get_img_from_url(imgUrl)
    print('img =', img)
    if img == None:
        return False
    name = str(uuid.uuid4()) + '.' + img.format.lower()
    savePath = os.path.join(ROOT_PATH, ANN_IMGBED_DIR, name)
    img.save(savePath)
    mydb, mycursor = new_sql_session()
    mycursor.execute("""replace into `muaAnnImgbed`
    (`img_name`, `img_url`, `create_time`) values
    (%s, %s, from_unixtime(%s))""",
                     (name, imgUrl, int(time.time())))
    return True


def img_url_to_img_path(imgUrl: str) -> Optional[str]:
    mydb, mycursor = new_sql_session()
    mycursor.execute("""
    select `img_name` from `muaAnnImgbed`
    where `img_url` = %s""", (imgUrl,))
    result = list(mycursor)
    if len(result) == 0:
        return None
    else:
        return os.path.join(ROOT_PATH, ANN_IMGBED_DIR, result[0][0])


def img_url_to_img_base64(imgUrl: str) -> Optional[str]:
    imgPath = img_url_to_img_path(imgUrl)
    if imgPath == None: return None
    img = Image.open(imgPath)
    imgData = BytesIO()
    img.save(imgData, format=img.format)
    b64img = base64.b64encode(imgData.getvalue()).decode('utf-8')
    return b64img


def url_or_base64_to_image(imgType: str, imgContent: str) -> Optional[Image.Image]:
    if imgType == 'imgurl':
        imgPath = img_url_to_img_path(imgContent)
        if imgPath != None:
            return Image.open(imgPath)
        else:
            req = requests.get(url=imgContent)
            if req.status_code == requests.codes.ok:
                try:
                    return Image.open(BytesIO(req.content))
                except Exception as e:
                    ic(e)
                    return None
            else:
                ic()
                return None
    elif imgType == 'imgbase64':
        try:
            return Image.open(BytesIO(base64.decode(imgContent)))
        except Exception as e:
            ic(e)
            return None
    else:
        ic()
        return None


def dump_msg_to_bed(msg: str):
    imgPattern = re.compile(r'\[CQ\:image\,file\=[^\,]+\,subType=\S+\,url\=([^\,]+)\]')
    for url in imgPattern.findall(msg):
        if dump_url_to_bed(url):
            print('dump OK: url =', url)
        else:
            print('dump fail: url =', url)


# if True:
if __name__ == '__main__':
    mydb, mycursor = new_sql_session()

    mycursor.execute("""
    select `img_url`,`img_name` from `muaAnnImgbed`
    limit 1""")
    result = list(mycursor)
    if len(result) == 0:
        print('测试失败，图床为空')
    else:
        imgUrl, imgName = result[0]
        picPath = img_url_to_img_path(imgUrl)
        print('img path:', picPath)
        b64img = img_url_to_img_base64(imgUrl)
        print(b64img)
