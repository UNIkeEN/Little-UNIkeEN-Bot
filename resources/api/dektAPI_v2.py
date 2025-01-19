import requests
from typing import List, Dict, Any, Optional
from urllib import parse
import base64

HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Cache-Control': 'max-age=0',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Microsoft Edge";v="120"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

def parseCookie(cookieStr:str)->Dict[str, str]:
    cookieDict = {}
    cookieStr = cookieStr.split(';')
    for cookie in cookieStr:
        cookie = cookie.strip().split('=')
        cookieDict[cookie[0].strip()] = cookie[1].strip()
    return cookieDict

def getJaccountOIDCToken(JAC_COOKIE:str, client_id:str)->Dict[str, str]:
    cookies = parseCookie(JAC_COOKIE)
    session = requests.session()
    req1 = session.get('https://jaccount.sjtu.edu.cn/oauth2/authorize', params={
                            'client_id': client_id,
                            'redirect_uri': 'https://activity.sjtu.edu.cn/auth',
                            'response_type': 'code',
                            'scope': 'profile',
                        }, cookies=cookies, headers=HEADERS)
    code = parse.parse_qs(parse.urlparse(req1.url).query)['code'][0]
    req2 = requests.get('https://activity.sjtu.edu.cn/api/v1/login/token', params={'code':code}, cookies=cookies, headers=HEADERS)
    token = req2.json()['data']
    return {'Authorization': 'Bearer '+token}

def getActivityTypes(JAC_COOKIE:str, client_id:str)->Optional[Dict[str, Any]]:
    headers = getJaccountOIDCToken(JAC_COOKIE, client_id)
    return requests.get(
        url='https://activity.sjtu.edu.cn/api/v1/system/activity_type',
        params={'isAll': 'true'}, 
        headers=headers
    ).json()["data"]
    
def getHotActivities(JAC_COOKIE:str, client_id:str, type_id: int = 1)->Optional[Dict[str, Any]]:
    headers = getJaccountOIDCToken(JAC_COOKIE, client_id)
    return requests.get(
        url='https://activity.sjtu.edu.cn/api/v1/hot/list', 
        params={
            'activity_type_id': type_id,
            'fill': '1',
        }, 
        headers=headers
    ).json()["data"]
    
def getAllActivities(JAC_COOKIE:str, client_id:str, 
                     type_id: int = 1, page: int = 1, page_size: int = 9)->Optional[Dict[str, Any]]:
    headers = getJaccountOIDCToken(JAC_COOKIE, client_id)
    resp = requests.get(
        url='https://activity.sjtu.edu.cn/api/v1/activity/list/home', 
        params={
            'page': page, ## 可翻页
            'per_page': page_size, 
            'activity_type_id': type_id,
            'time_sort': 'desc',
            # 'can_apply': 'true',
        }, 
        headers=headers
    ).json()["data"]
    return sorted(resp, key=lambda x: x['activity_time'][0], reverse=True)


def actIdToUrlParam(activityId:int) -> str:
    idStr = str(activityId)
    idStr = idStr + ' ' * ((3 - len(idStr)%3) % 3)
    return base64.b64encode(idStr.encode('utf-8')).decode('utf-8')
