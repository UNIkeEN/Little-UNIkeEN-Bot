import requests
from typing import List, Dict, Any, Optional

def parseCookie(cookieStr:str)->Dict[str, str]:
    cookieDict = {}
    cookieStr = cookieStr.split(';')
    for cookie in cookieStr:
        cookie = cookie.strip().split('=')
        cookieDict[cookie[0].strip()] = cookie[1].strip()
    return cookieDict

def getCharge(JAC_COOKIE:str, client_id:str, url:str)->Optional[List[Dict[str, Any]]]:
    cookies = parseCookie(JAC_COOKIE)
    headers = {
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

    session = requests.session()
    session.get('https://jaccount.sjtu.edu.cn/oauth2/authorize',
            params={
                'scope':'essential',
                'response_type':'code',
                'redirect_uri':'https://e-mobile.sjtu.edu.cn',
                'client_id': client_id,
            }, cookies=cookies, headers=headers,allow_redirects=True)
    # print(session.cookies)
    result = []
    for page in [1, 2]:
        params = {
            'longitude': '0',
            'latitude': '0',
            'instance': '',
            'power': '',
            'fees': '',
            'deviceStatus': '',
            'websiteName': '',
            'websiteId': '',
            'portStatus': '',
            'limit': '100',
            'page': str(page),
        }
        response = session.get(url,params=params,cookies=cookies,headers=headers)
        if response.status_code != 200:
            continue
        try:
            response = response.json()
            errno = int(response['errno'])
            if errno != 0: continue
            result += response['data']
        except:
            continue
    if len(result) == 0:
        return None
    return result
if __name__ == '__main__':
    print(getCharge())