# https://socialsisteryi.github.io/bilibili-API-collect/docs/misc/sign/wbi.html#python

import time
import urllib.parse
from functools import reduce
from hashlib import md5

import requests

mixinKeyEncTab = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]

def getMixinKey(orig: str):
    '对 imgKey 和 subKey 进行字符顺序打乱编码'
    return reduce(lambda s, i: s + orig[i], mixinKeyEncTab, '')[:32]

def encWbi(params: dict, img_key: str, sub_key: str):
    '为请求参数进行 wbi 签名'
    mixin_key = getMixinKey(img_key + sub_key)
    curr_time = round(time.time())
    params['wts'] = curr_time                                   # 添加 wts 字段
    params = dict(sorted(params.items()))                       # 按照 key 重排参数
    # 过滤 value 中的 "!'()*" 字符
    params = {
        k : ''.join(filter(lambda chr: chr not in "!'()*", str(v)))
        for k, v 
        in params.items()
    }
    query = urllib.parse.urlencode(params)                      # 序列化参数
    wbi_sign = md5((query + mixin_key).encode()).hexdigest()    # 计算 w_rid
    params['w_rid'] = wbi_sign
    return params

def getWbiKeys() -> tuple[str, str]:
    '获取最新的 img_key 和 sub_key'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'Referer': 'https://www.bilibili.com/'
    }
    resp = requests.get('https://api.bilibili.com/x/web-interface/nav', headers=headers)
    resp.raise_for_status()
    json_content = resp.json()
    img_url: str = json_content['data']['wbi_img']['img_url']
    sub_url: str = json_content['data']['wbi_img']['sub_url']
    img_key = img_url.rsplit('/', 1)[1].split('.')[0]
    sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
    return img_key, sub_key

if __name__ == '__main__':
    img_key, sub_key = getWbiKeys()
    url = 'https://api.bilibili.com/x/space/wbi/acc/info'
    signed_params = encWbi(
        params = {
            "mid": "1784797361",
            "token": "",
            "platform": "web",
            "web_location": "1550101",
            "w_webid": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzcG1faWQiOiIwLjAiLCJidXZpZCI6Ijc4NDExRTYxLTQ3REYtNzQ4NC1FQ0ZBLTcwN0YxQUI5NDg2RTk1MjIxaW5mb2MiLCJ1c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFgxMTsgTGludXggeDg2XzY0KSBBcHBsZVdlYktpdC81MzcuMzYgKEtIVE1MLCBsaWtlIEdlY2tvKSBDaHJvbWUvMTMyLjAuMC4wIFNhZmFyaS81MzcuMzYgRWRnLzEzMi4wLjAuMCIsImJ1dmlkX2ZwIjoiZGQwMGI2YzcyZGM4NzhlYmQxMDU1ZWJhYzVlZmZhMjkiLCJiaWxpX3RpY2tldCI6IjJkOWNmNzQxMDg0NDc0YjQ2YjkzZTFjYzRjMDBkYzkyIiwiY3JlYXRlZF9hdCI6MTczMzc1MjU4MSwidHRsIjo4NjQwMCwidXJsIjoiLzE3ODQ3OTczNjE_c3BtX2lkX2Zyb209MzMzLjEwMDcudGlhbm1hLjEtMS0xLmNsaWNrIiwicmVzdWx0Ijoibm9ybWFsIiwiaXNzIjoiZ2FpYSIsImlhdCI6MTczMzc1MjU4MX0.izNUcQUV2ZDAeDWdSJG60z8v7kBDHgWfLd6riRm1msZWgtY2NvXtWPZAOJY0dzmPRueXCBWPFrBC30bzgkAE3v9Gg7dVGLttPweidH3XyvSX2rEylTdKQN4HLcKLl77quV8FW6aKCgnHm5LJ_nVhLZgVbTMk-rk0v2jJ_HSRboxwmj5uaM22EiE4ZHdBnedgiFZ5f2pEoPsl_3d1L8d8vHCUTIsDzwRGOOFzx0xHn3U41S0MksmqtOjS2-J2oECkKGV6LW5b7TtgyrmQD6_ZTNIS3cl6nfeW_tnTr3a0J19wiKvz0SdoM6ajzKzXAlwnNs_xfWxWWNrLd4y-vQkazg",
        },
        img_key=img_key,
        sub_key=sub_key
    )
    query = urllib.parse.urlencode(signed_params)
    print(signed_params)
    print(url+'?'+query)
