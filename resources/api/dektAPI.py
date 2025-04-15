import time
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import requests


def parseCookie(cookieStr:str)->Dict[str, str]:
    cookieDict = {}
    cookieStr = cookieStr.split(';')
    for cookie in cookieStr:
        cookie = cookie.strip().split('=')
        cookieDict[cookie[0].strip()] = cookie[1].strip()
    return cookieDict

def getDekt(JAC_COOKIE:str, client_id:str, curUserId:str)->Optional[Dict[str, List[Dict[str, Any]]]]:
    timeStamp = str(int(time.time() * 1000))
    session = requests.session()
    req1 = session.get('https://jaccount.sjtu.edu.cn/oauth2/authorize', 
                        params={
                            'response_type': 'code',
                            'client_id': client_id,
                            'redirect_uri': 'https://dekt.sjtu.edu.cn/h5/index',
                            'state':'',
                            'scope':'basic',
                        },
                        cookies=parseCookie(JAC_COOKIE),
                        allow_redirects=True)
    if 'jaccount' in req1.text: return None
    reqCode = parse_qs(urlparse(req1.url).query)['code'][0]
    req2 = session.post('https://dekt.sjtu.edu.cn/api/auth/secondclass/loginByJa',
        params={
            'time': timeStamp,
            'publicaccountid': 'sjtuvirtual'
        },
        headers={
            'jtoken': 'null',
            'curUserId': 'null',
            'publicaccountid': 'sjtuvirtual',
            'tenantId': 'null',
            'token': 'null',
        },
        json= {
            'code': reqCode,
            'redirect_uri': 'https://dekt.sjtu.edu.cn/h5/index',
            'scope': 'basic',
            'client_id': client_id,
            'publicaccountid': 'sjtuvirtual',
        },
    )
    if req2.status_code != requests.codes.ok:
        return None
    token = req2.json()['data']
    req3 = session.post('https://dekt.sjtu.edu.cn/api/wmt/secondclass/fmGetNewestActivityList',
        params={
            'time': timeStamp,
            'tenantId': '500',
            'token': token['token'],
            'publicaccountid': 'sjtuvirtual',
        },
        headers={
            'curUserId': curUserId,
            'jtoken': token['jtoken'],
            'publicaccountid': 'sjtuvirtual',
            'token': token['token'],
        },
        json = {
            'publicaccountid': 'sjtuvirtual',
        },
    )
    result = req3.json()
    if result['code'] != 0: return None
    return result
