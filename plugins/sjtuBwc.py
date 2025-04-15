import datetime
import time
from threading import Semaphore
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

import pyjsparser.parser as jsparser
import requests
from bs4 import BeautifulSoup as BS

from utils.basicEvent import send, warning
from utils.configAPI import getPluginEnabledGroups
from utils.sqlUtils import newSqlSession
from utils.standardPlugin import CronStandardPlugin, StandardPlugin


def createBwcSql():
    mydb, mycursor = newSqlSession()
    mycursor.execute("""
    create table if not exists `bwcRecord`(
        `msgid` bigint unsigned not null,
        `create_time` timestamp default null,
        `title` varchar(300) default null,
        `url` varchar(500) default null,
        primary key(`msgid`)
    )charset=utf8mb4, collate=utf8mb4_unicode_ci;""")

def simplifyWxappUrl(url:str):
    up = urlparse(url)
    query = []
    for u in up.query.split('&amp;'):
        u = u.split('=', maxsplit=1)
        if u[0] not in ['chksm']:
            query.append((u[0], u[1]))
    query = '&amp;'.join('{}={}'.format(k, v) for k, v in query)
    url = '%s://%s%s?%s'%(up.scheme, up.netloc, up.path, query)
    return url

def getBwcNotice()->Optional[List[Dict]]:
    """@return:
        if "OK": [{
            'title': str,
            'create_time': int,
            'msgid': int,
            'url': str,
            'cover_img_1_1': str
        }]
        else:
            None
    """

    url = 'https://mp.weixin.qq.com/mp/appmsgalbum?__biz=MzA3MzMzMDIzNg==&action=getalbum&album_id=2034335777152614400&from_msgid=2649562310'
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',''
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'cache-control': 'max-age=0',
        'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Microsoft Edge";v="110"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36 Edg/110.0.0.0',
    }
    req = requests.get(url=url, headers=headers)
    html = BS(req.text, 'lxml')
    targetJs = None
    for js in html.find_all('script', ):
        if len(js.contents) > 0 and 'window.cgiData' in js.contents[0]:
            targetJs = js.contents[0]
            break
    if targetJs == None: return None
    try:
        results = []
        jsAst = jsparser.parse(targetJs)
        properties = jsAst['body'][0]['expression']['right']['properties']
        articleList = None
        for p in properties:
            if p['key']['name'] == 'articleList':
                articleList = p['value']['elements']
                break
        if articleList == None: return None
        for element in articleList:
            result = {}
            for p in element['properties']:
                if p['type'] != 'Property': continue
                keyName = p['key']['name']
                if keyName in ['title', 'create_time', 'msgid', 'url', 'cover_img_1_1']:
                    if keyName in ['create_time', 'msgid']:
                        result[keyName] = int(p['value']['value'])
                    else:
                        result[keyName] = p['value']['value']
            results.append(result)
        return results
    except Exception as e:
        warning('js parse error in sjtuBwc: {}'.format(e))
        return None

class SjtuBwc(StandardPlugin): 
    initGuard = Semaphore()
    def __init__(self):
        if self.initGuard.acquire(blocking=False):
            createBwcSql()
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg=='-bwc'
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        bwc = sorted(getBwcNotice(), key=lambda x: x['create_time'], reverse=True)
        bwcStr = '\n\n'.join(['【%d】%s\n%s\n%s'%(
            idx+1, datetime.datetime.fromtimestamp(b['create_time']).strftime('%Y-%m-%d %H:%M'), 
            b['title'], simplifyWxappUrl(b['url']))
            for idx, b in enumerate(bwc[:5])])
        send(target, bwcStr, data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'SjtuBwc',
            'description': '获取保卫处通知',
            'commandDescription': '-bwc',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': ['bwcRecord'],
            'version': '1.0.0',
            'author': 'Unicorn',
        }

class SjtuBwcMonitor(StandardPlugin, CronStandardPlugin):
    guardSem = Semaphore()
    @staticmethod
    def checkAndUpdate(notices:List[Dict])->List[Dict]:
        """检测notices中的元素是否曾被记录过，记录没有被记录过的元素，并返回没有被记录过的元素列表
        @notices: [{
            'title': str,
            'create_time': int,
            'msgid': int,
            'url': str,
            'cover_img_1_1': str
        }, ....]

        @return: 如果某个元素没被记录，则返回值会append
        """
        result = []
        mydb, mycursor = newSqlSession()

        for notice in notices:
            mycursor.execute("""select count(*) from `bwcRecord`
            where msgid = %d
            """%notice['msgid'])
            count = list(mycursor)[0][0]
            if count == 0:
                result.append(notice)
                mycursor.execute("""insert into `bwcRecord` set
                `msgid` = %s,
                `create_time` = from_unixtime(%s),
                `title` = %s,
                `url` = %s
                """, (
                    notice['msgid'],
                    notice['create_time'],
                    notice['title'],
                    notice['url']
                ))
        return result
    def __init__(self) -> None:
        if SjtuBwcMonitor.guardSem.acquire(blocking=False):
            self.start(0, 3 * 60)
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return False
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        return None
    def tick(self) -> None:
        notices = getBwcNotice()
        notices = self.checkAndUpdate(notices)
        for group_id in getPluginEnabledGroups('bwcreport'):
            for notice in notices:
                send(group_id, '已发现保卫处通知更新:\n%s\n\n%s\n\n%s'%(
                    datetime.datetime.fromtimestamp(notice['create_time']).strftime('%Y-%m-%d %H:%M'), 
                    notice['title'], simplifyWxappUrl(notice['url'])
                ))
                time.sleep(1)

    def checkSelfStatus(self):
        if getBwcNotice() != None:
            return 1, 1, '正常'
        else:
            return 1, 0, '获取bwc内容失败'

    def getPluginInfo(self) -> dict:
        return {
            'name': 'SjtuBwcMonitor',
            'description': '保卫处通知更新广播',
            'commandDescription': '[-grpcfg驱动]',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }

if __name__ == '__main__':
    print(getBwcNotice())