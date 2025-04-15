from typing import Any, Dict, List, Optional

import requests


def parseCookie(cookieStr:str)->Dict[str, str]:
    cookieDict = {}
    cookieStr = cookieStr.split(';')
    for cookie in cookieStr:
        cookie = cookie.strip().split('=')
        cookieDict[cookie[0].strip()] = cookie[1].strip()
    return cookieDict


def getCourses(JAC_COOKIE:str, 
               client_id:str, 
               params:Dict[str, str],
               data:Dict[str, str])->Optional[List[Dict[str, Any]]]:
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
                    'redirect_uri':'http://i.sjtu.edu.cn/jaccountlogin',
                    'client_id': client_id,
                }, cookies=cookies, headers=headers,allow_redirects=True)
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'Origin': 'https://i.sjtu.edu.cn',
        'Referer': 'https://i.sjtu.edu.cn/design/viewFunc_cxDesignFuncPageIndex.html?gnmkdm=N2199113&layout=default',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
        'X-Requested-With': 'XMLHttpRequest',
        'sec-ch-ua': '"Microsoft Edge";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
    }

    try:
        r = session.post(
            'https://i.sjtu.edu.cn/design/funcData_cxFuncDataList.html',
            params=params,
            cookies=cookies,
            headers=headers,
            data=data,
        )
        return r.json()['items']
    except:
        return None

if __name__ == '__main__':
    print(getCourses())