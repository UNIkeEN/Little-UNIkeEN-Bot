from datetime import datetime
import re
import time
import requests
from typing import List, Tuple, Optional, Union, Dict, Any, Set
from bs4 import BeautifulSoup
HEADERS = {
        "authority": "edith.xiaohongshu.com",
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "content-type": "application/json;charset=UTF-8",
        "origin": "https://www.xiaohongshu.com",
        "referer": "https://www.xiaohongshu.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 Edg/115.0.1901.188",
        "x-s": "",
        "x-t": ""
    }


class UserNotFound(Exception):
    def __init__(self, message):
        super().__init__(message)


class UserFixed():
    def __init__(self, luid: str):
        self.luid = luid
        self.nickname = None
        try:
            self.init_nickname()
        except:
            raise UserNotFound("User Not Found")
        # long uid eg:5c138a13000000000501e889
        
    def get_url(self) ->str:
        return "https://www.xiaohongshu.com/user/profile/" + self.luid

    def get_luid(self) -> str:
        return self.luid

    def get_user_page(self) -> str:
        url = self.get_url()
        response = requests.get(url, headers=HEADERS)
        html_text = response.text
        return html_text

    def init_nickname(self) -> None:
        # 解析html的方式有些奇怪，以后有空再改
        true, false, null, undefined = True, False, None, None
        html_text = self.get_user_page()
        info = re.findall(r'<script>window.__INITIAL_STATE__=(.*?)</script>', html_text)[0]
        info = eval(info)
        self.nickname=  info['user']['userPageData']['basicInfo']['nickname']

    def get_nickname(self) -> str:
        return self.nickname    
    
    # 多条动态，时间为序
    def get_dynamics(self, need_top: bool = True, base = 1, limit = 5) -> list:
        note_id_list = []
        true, false, null, undefined = True, False, None, None
        html_text = self.get_user_page()
        info = re.findall(r'<script>window.__INITIAL_STATE__=(.*?)</script>', html_text)[0]
        info = eval(info)
        note_list = info['user']['notes'][0]
        num_note = len(note_list)
        for i in range(base-1, min(limit, num_note)):
            note = note_list[i]
            if (not need_top):
                if (note['noteCard']['interactInfo']['sticky']):
                    continue
            note_item = {}
            nid = note['id']
            note_item['note_id'] = nid

            url = "https://www.xiaohongshu.com/explore/" + nid
            response = requests.get(url, headers=HEADERS)
            html_text = response.text
            soup = BeautifulSoup(html_text, 'html.parser')
            note_item['title'] = self.get_dynamics_title(soup)
            note_item['uname'] = self.get_nickname()
            note_item['pub_location'] = self.get_dynamics_ip(soup)
            note_item['pic'] = note['noteCard']['cover']['infoList'][1]['url']
            desc = self.get_dynamics_desc(soup)
            note_item['desc'] = desc
            note_item['timestp'] = self.get_dynamics_timpstamp(html_text,nid)
            note_item['date'] = self.get_dynamics_date(note_item['timestp'])
            note_id_list.append(note_item)

        
        return note_id_list
    
    # 获取发表时间
    def get_dynamics_date(self, timestamp):
        
        date_str = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(timestamp))
        return date_str
        

    # 获取发表时间戳
    def get_dynamics_timpstamp(self, html_text,nid):
        try:
            true, false, null, undefined = True, False, None, None
            info = re.findall(r'<script>window.__INITIAL_STATE__=(.*?)</script>', html_text)[0]
            info = eval(info)
            timestp  = info['note']['noteDetailMap'][nid]['note']["time"]
            return int(timestp)//1000
        except:
            return ''


    #ip属地
    def get_dynamics_ip(self, soup):
        try:
            return soup.find('span', class_="date").text.split(" ")[1]
        except:
            return ""
    # 笔记标题  
    def get_dynamics_title(self, soup):
        try:
            title_str = soup.find('div', id = 'detail-title').text
            return title_str
        except:
            return ''
    # 笔记描述
    def get_dynamics_desc(self, soup):
        try:
            desc_str = soup.find('div', id = 'detail-desc').find('span').text
            return desc_str
        except:
            return ''

    def get_user_info(self):
        return {'name':self.nickname, 'mid':self.luid}



if __name__ == '__main__':
    #user = UserFixed("6185ce66000000001000705b")
    user = UserFixed('5c138a13000000000501e889')
    #print(user.get_user_info())
    #print(user.get_nickname())
    print(user.get_dynamics(need_top= False)[0])
    #print(user.get_dynamics_desc('65aca7b2000000002d00e9f3'))