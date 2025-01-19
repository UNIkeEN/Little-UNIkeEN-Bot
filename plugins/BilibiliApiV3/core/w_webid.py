# https://github.com/SocialSisterYi/bilibili-API-collect/issues/1107

import requests
import re
import json
import urllib

def get_w_webid(self_uid:int, )->str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        "Referer": "https://www.bilibili.com/",
        "Cookie": "<cookie>",
    }

    dynamic_url = f"https://space.bilibili.com/{self_uid}/dynamic"

    text = requests.get(dynamic_url, headers=headers).text
    # print(text)
    __RENDER_DATA__ = re.search(
        r"<script id=\"__RENDER_DATA__\" type=\"application/json\">(.*?)</script>",
        text,
        re.S,
    ).group(1)

    access_id = json.loads(urllib.parse.unquote(__RENDER_DATA__))["access_id"]
    return access_id

if __name__ == "__main__":
    get_w_webid(437994974)