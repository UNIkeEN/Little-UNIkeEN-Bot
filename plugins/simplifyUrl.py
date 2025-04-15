from enum import IntEnum
from typing import Any, Tuple, Union
from urllib.parse import ParseResult, parse_qs, urljoin, urlparse

from urlextract import URLExtract

from utils.standardPlugin import StandardPlugin


class URL_TYPE(IntEnum):
    UNKNOWN = 0
    DOUYIN = 10
    XHS = 20
    BILIBILI = 30
    SHUIYUAN = 40
    WEIXIN = 50
    ZHIHU = 60
    WEIBO = 70
    WEIXIN = 80
    QQ = 90
    BAIDU = 100
    BAIDU_BJH = 101
    BAIDU_MBD = 102
    
def classifyUrl(netloc:str)->URL_TYPE:
    return {
        'www.xiaohongshu.com': URL_TYPE.XHS,
        'xiaohongshu.com': URL_TYPE.XHS,
        'www.bilibili.com': URL_TYPE.BILIBILI,
        'bilibili.com': URL_TYPE.BILIBILI,
        'b23.tv': URL_TYPE.BILIBILI,
        'shuiyuan.sjtu.edu.cn': URL_TYPE.SHUIYUAN,
        'www.zhihu.com': URL_TYPE.ZHIHU,
        'zhihu.com': URL_TYPE.ZHIHU,
        'www.weibo.com': URL_TYPE.WEIBO,
        'weibo.com': URL_TYPE.WEIBO,
        'mp.weixin.qq.com': URL_TYPE.WEIXIN,
        'www.baidu.com': URL_TYPE.BAIDU,
        'baidu.com': URL_TYPE.BAIDU,
        'mbd.baidu.com': URL_TYPE.BAIDU_MBD,
        'baijiahao.baidu.com': URL_TYPE.BAIDU_BJH,
    }.get(netloc, URL_TYPE.UNKNOWN)
    
def removeTackingParams(up:ParseResult)->str:
    return up.encode

def simplifyUrl(url:str)->Tuple[bool, str]:
    up = urlparse(url)
    utype = classifyUrl(up.netloc)
    if utype == URL_TYPE.UNKNOWN:
        return False, '未知源'
    
class SimplifyUrl(StandardPlugin):
    def __init__(self) -> None:
        self.extractor = URLExtract(extract_localhost=False)
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return data['message_type']=='group'
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        urls = self.extractor.find_urls(msg)
        if len(urls) == 0: return None
        
        return None
    def getPluginInfo(self, )->Any:
        return {
            'name': 'SimplifyUrl',
            'description': '去除url追踪参数',
            'commandDescription': '自动识别',
            'usePlace': ['group',  ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }