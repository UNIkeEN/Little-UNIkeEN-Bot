import time
import urllib.parse

import execjs
import requests

from .xhs_api import UserNotFound

HEADERS = {
    'authority': 'www.douyin.com',
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'cache-control': 'no-cache',
    'cookie': 'ttwid=1%7CcJGI67aWpn4SE9PnraRLYycOmzrf1HaGT3LyRU73XeQ%7C1706102741%7C20de9ee9e416dda39f2b8f0a41f91853452d7fa348bd93f51c70963a4c50357e; douyin.com; device_web_cpu_core=12; device_web_memory_size=8; architecture=amd64; dy_swidth=1707; dy_sheight=1067; FORCE_LOGIN=%7B%22videoConsumedRemainSeconds%22%3A180%7D; csrf_session_id=5ed2d653a174ca91beb16457aa3d9a8f; strategyABtestKey=%221706102748.397%22; volume_info=%7B%22isUserMute%22%3Afalse%2C%22isMute%22%3Afalse%2C%22volume%22%3A0.6%7D; passport_csrf_token=840d6ca3242406573e450f92d87e5b08; passport_csrf_token_default=840d6ca3242406573e450f92d87e5b08; bd_ticket_guard_client_web_domain=2; stream_player_status_params=%22%7B%5C%22is_auto_play%5C%22%3A0%2C%5C%22is_full_screen%5C%22%3A0%2C%5C%22is_full_webscreen%5C%22%3A0%2C%5C%22is_mute%5C%22%3A0%2C%5C%22is_speed%5C%22%3A1%2C%5C%22is_visible%5C%22%3A0%7D%22; __ac_nonce=065b10fe000ec88189f5f; __ac_signature=_02B4Z6wo00f01KyZrOQAAIDD2rZxqmn5JhisuahAAE6c020m1qir53kqSP2hjOjel2ForL-O6OJ1QyzaF.KHnkmOv9NVF7FwWxZn6F9ol1UCCneFA0dgqm1rfeeq8M9ovnu-3qfw6VBUTn.75e; SEARCH_RESULT_LIST_TYPE=%22single%22; pwa2=%220%7C0%7C2%7C0%22; stream_recommend_feed_params=%22%7B%5C%22cookie_enabled%5C%22%3Atrue%2C%5C%22screen_width%5C%22%3A1707%2C%5C%22screen_height%5C%22%3A1067%2C%5C%22browser_online%5C%22%3Atrue%2C%5C%22cpu_core_num%5C%22%3A12%2C%5C%22device_memory%5C%22%3A8%2C%5C%22downlink%5C%22%3A10%2C%5C%22effective_type%5C%22%3A%5C%224g%5C%22%2C%5C%22round_trip_time%5C%22%3A50%7D%22; IsDouyinActive=true; home_can_add_dy_2_desktop=%221%22; bd_ticket_guard_client_data=eyJiZC10aWNrZXQtZ3VhcmQtdmVyc2lvbiI6MiwiYmQtdGlja2V0LWd1YXJkLWl0ZXJhdGlvbi12ZXJzaW9uIjoxLCJiZC10aWNrZXQtZ3VhcmQtcmVlLXB1YmxpYy1rZXkiOiJCQTVxNGlKUGRaMGo4WEFBZlQydTJ6aytBRzV1ZUx5aUJvZjFINk1ad3FQY2duV3lWZERHTStTTzdUai9yWUlZMXFVbVllMSs4YWJBU3Uxei9Ra00yUkk9IiwiYmQtdGlja2V0LWd1YXJkLXdlYi12ZXJzaW9uIjoxfQ%3D%3D; msToken=nRngJftq1M9-TTEQltVQ1mLRFNOpA0mM5yHDNnjOlxbDb3MK7ZzfI17UoCS-1weTn3TLkWU6-g0Q4dHH8-3hSF106UKVCtWS4XEL0vrVuMAi_G9Kg2iAR6Ohid_0r3OciA==; tt_scid=ZOcV-94cBw3qktEmfDvdfByk6eUk..pq-O5S6JqK0vHitjj4nmzLBKDODnSMaYts0e56; msToken=R3Zt3LCgzNMbVUcwcRT2g85qIANbGYIEw25oApjp_QXwpIfoq9O6usotWcb3ZYgRI1vs--mwdDJxvsgXdkYLG3ge8PemrCrkYM5xA0IlHqI4jbadSwx1aj0z6rFSzTTR; download_guide=%223%2F20240124%2F0%22',
    'pragma': 'no-cache',
    'referer': 'https://www.douyin.com/user/MS4wLjABAAAAhyMOxQb89aowXcg9pyhQbBjqpvHa3_EqN9PDrH2GBez1FnjMZzYTn0XILXXGu9o_',
    'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Microsoft Edge";v="120"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
}

DEFAULT_PARAMS = {
        "device_platform": "webapp",
        "aid": "6383",
        "channel": "channel_pc_web",
        "publish_video_strategy_type": "2",
        "source": "channel_pc_web",
        "sec_user_id": "",
        "pc_client_type": "1",
        "version_code": "170400",
        "version_name": "17.4.0",
        "cookie_enabled": "true",
        "screen_width": "1707",
        "screen_height": "1067",
        "browser_language": "zh-CN",
        "browser_platform": "Win32",
        "browser_name": "Edge",
        "browser_version": "117.0.2045.47",
        "browser_online": "true",
        "engine_name": "Blink",
        "engine_version": "117.0.0.0",
        "os_name": "Windows",
        "os_version": "10",
        "cpu_core_num": "20",
        "device_memory": "8",
        "platform": "PC",
        "downlink": "10",
        "effective_type": "4g",
        "round_trip_time": "50",
        # "webid": "7285671865124996668",
        'X-Bogus': ''
    }

COOKIES = {'webid': '7327655416719967782',
        'msToken': '728WeFdMnp_zG-RwePulDZ30OQ-GKw_3BSRrwm0vsMMMYhLqlH9oqM5mbFJ4ttZVhexcMy1cu6LBSTKykmRPTr9dSjwAx8E-H0Ysb_hSzO04axrMSZN7AQc0fJW2wmIGjA==',
}


def splice_url(params):
    splice_url_str = ''
    for key, value in params.items():
        if value is None:
            value = ''
        splice_url_str += key + '=' + value + '&'
    return splice_url_str[:-1]



class UserFixed:
    def __init__(self, sid:str) -> None:
        self.uid = None
        # secure id 万恶的加密id
        self.sid = sid
        self.nickname = self.get_dynamics()[0]['uname']

    def init_info(self):
        pass

    def get_dynamics(self, need_top: bool = True, base = 1, limit = 5) -> list:
        params = DEFAULT_PARAMS.copy()

        params['sec_user_id'] = self.sid
        url = 'https://www.douyin.com/aweme/v1/web/aweme/post/' + '?' + splice_url(params)

        query = urllib.parse.urlparse(url).query
        xbogus = execjs.compile(open('./resources/X-Bogus.js').read()).call('sign', query, HEADERS['user-agent'])
        new_url = url + "&X-Bogus=" + xbogus


        aweme_list = requests.get(new_url, headers=HEADERS).json()["aweme_list"]
        aweme_list_new = []
        for aweme in aweme_list:
            if ((not need_top) and  aweme['is_top']):
                continue
            aweme_item = {}
            aweme_item['luid'] = self.sid
            aweme_item['url'] = aweme['share_info']['share_url'].split("?")[0]
            aweme_item['uname'] = aweme['author']['nickname']
            aweme_item['aid'] = int(aweme['aweme_id'])
            aweme_item['pic'] = aweme['video']['cover']['url_list'][0]
            aweme_item['desc'] = aweme['desc']
            aweme_item['timestp'] = aweme['create_time']
            aweme_item['date'] = self.get_dynamics_date(aweme['create_time'])
            aweme_item['pub_location'] = ''
            aweme_list_new.append(aweme_item)

        return aweme_list_new
    
    def get_dynamics_date(self, timestamp):
        return time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(timestamp))


    def get_dynamics_ip(self):
        pass

    def get_nickname(self):
        return self.nickname
    
    def get_user_info(self):
        return {'name':self.nickname, "mid" :self.sid}

if __name__ == "__main__":
    #user = UserFixed("MS4wLjABAAAAhyMOxQb89aowXcg9pyhQbBjqpvHa3_EqN9PDrH2GBez1FnjMZzYTn0XILXXGu9o_")
    user = UserFixed('MS4wLjABAAAA6oXfkmTKed1XhrJDV6A7pEl4lModpnb4_pQmMO2joNo')
    print(user.get_dynamics(need_top=False)[0])
