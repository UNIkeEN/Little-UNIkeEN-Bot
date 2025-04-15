"""
由 bilibili-api 二次开发
源仓库: https://github.com/MoyuScript/bilibili-api
"""

import json
import time
from enum import Enum
from typing import Dict, List

from deprecated import deprecated

from utils.basicEvent import warning

from ..starbot_utils.Credential import Credential
from ..starbot_utils.network import request
from ..starbot_utils.utils import get_api
from .wbi import encWbi, getWbiKeys

API = get_api("user")


class VideoOrder(Enum):
    """
    视频排序顺序

    + PUBDATE  : 上传日期倒序
    + FAVORITE : 收藏量倒序
    + VIEW     : 播放量倒序
    """
    PUBDATE = "pubdate"
    FAVORITE = "stow"
    VIEW = "click"


class AudioOrder(Enum):
    """
    音频排序顺序

    + PUBDATE  : 上传日期倒序
    + VIEW     : 播放量倒序
    + FAVORITE : 收藏量倒序
    """
    PUBDATE = 1
    VIEW = 2
    FAVORITE = 3


class ArticleOrder(Enum):
    """
    专栏排序顺序

    + PUBDATE  : 发布日期倒序
    + FAVORITE : 收藏量倒序
    + VIEW     : 阅读量倒序
    """
    PUBDATE = "publish_time"
    FAVORITE = "fav"
    VIEW = "view"


class ArticleListOrder(Enum):
    """
    文集排序顺序

    + LATEST : 最近更新倒序
    + VIEW   : 总阅读量倒序
    """
    LATEST = 0
    VIEW = 1


class BangumiType(Enum):
    """
    番剧类型

    + BANGUMI : 番剧
    + DRAMA   : 电视剧/纪录片等
    """
    BANGUMI = 1
    DRAMA = 2


class RelationType(Enum):
    """
    用户关系操作类型

    + SUBSCRIBE          : 关注
    + UNSUBSCRIBE        : 取关
    + SUBSCRIBE_SECRETLY : 悄悄关注
    + BLOCK              : 拉黑
    + UNBLOCK            : 取消拉黑
    + REMOVE_FANS        : 移除粉丝
    """
    SUBSCRIBE = 1
    UNSUBSCRIBE = 2
    SUBSCRIBE_SECRETLY = 3
    BLOCK = 5
    UNBLOCK = 6
    REMOVE_FANS = 7

# for debug
def format_url(url:str, params:Dict[str, str])->str:
    return url + '?' + '&'.join(['{}={}'.format(k, v) for k, v in params.items()])

class User:
    """
    用户相关
    """

    def __init__(self, 
                 uid: int, 
                 credential: Credential = None, 
                 wbi_keys: Dict[str, str] = None,
                 w_webid: str = None):
        """
        Args:
            uid: 用户 UID
            credential: 凭据。默认：None
        """
        self.uid = uid

        if credential is None:
            credential = Credential()
        self.credential = credential
        self.__self_info = None
        self.__wbi_keys = wbi_keys
        self.__w_webid = w_webid
    
    def set_wbi_keys(self, wbi_keys: Dict[str, str], w_webid: str) -> None:
        self.__wbi_keys = wbi_keys
        self.__w_webid = w_webid
        
    @deprecated(reason='you should use get_user_info_wbi')
    async def get_user_info(self):
        """
        获取用户信息（昵称，性别，生日，签名，头像 URL，空间横幅 URL 等）
        """
        api = API["info"]["info"]
        params = {
            "mid": self.uid
        }
        return await request("GET", url=api["url"], params=params, credential=self.credential)

    async def get_user_info_wbi(self):
        if self.__wbi_keys == None:
            raise RuntimeError("wbi keys is None")
        api = API["info"]["info_wbi"]
        params = {
            "mid": self.uid,
            "web_location": '333.999',
            "w_webid": self.__w_webid,
        }
        params_wbi = encWbi(params, **self.__wbi_keys)
        # debug_url = format_url(api["url"], params_wbi)
        return await request("GET", url=api["url"], params=params_wbi, credential=self.credential)
    
    async def __get_self_info(self):
        """
        获取自己的信息，如果存在缓存则使用缓存
        """
        if self.__self_info is not None:
            return self.__self_info

        self.__self_info = await get_self_info(credential=self.credential)
        return self.__self_info

    async def get_relation_info(self):
        """
        获取用户关系信息（关注数，粉丝数，悄悄关注，黑名单数）
        """
        api = API["info"]["relation"]
        params = {
            "vmid": self.uid
        }
        return await request("GET", url=api["url"], params=params, credential=self.credential)

    async def get_up_stat(self):
        """
        获取 UP 主数据信息（视频总播放量，文章总阅读量，总点赞数）
        """
        self.credential.raise_for_no_bili_jct()

        api = API["info"]["upstat"]
        params = {
            "mid": self.uid
        }
        return await request("GET", url=api["url"], params=params, credential=self.credential)

    @deprecated(reason="you should use get_live_info_wbi")
    async def get_live_info(self):
        """
        获取用户直播间信息
        """
        api = API["info"]["live"]
        params = {
            "mid": self.uid
        }
        return await request("GET", url=api["url"], params=params, credential=self.credential)

    async def get_live_info_wbi(self):
        """
        获取用户直播间信息
        """
        if self.__wbi_keys == None:
            raise RuntimeError("wbi keys is None")
        api = API["info"]["live_wbi"]
        params = {
            "mid": self.uid
        }
        params_wbi = encWbi(params, **self.__wbi_keys)
        return await request("GET", url=api["url"], params=params_wbi, credential=self.credential)
    
    async def get_videos(self,
                         tid: int = 0,
                         pn: int = 1,
                         keyword: str = "",
                         order: VideoOrder = VideoOrder.PUBDATE
                         ):
        """
        获取用户投稿视频信息

        Args:
            tid: 分区 ID。默认：0（全部）
            pn: 页码，从 1 开始。默认：1
            keyword: 搜索关键词。默认：""
            order: 排序方式。默认：VideoOrder.PUBDATE
        """
        api = API["info"]["video"]
        params = {
            "mid": self.uid,
            "ps": 30,
            "tid": tid,
            "pn": pn,
            "keyword": keyword,
            "order": order.value
        }
        return await request("GET", url=api["url"], params=params, credential=self.credential)

    async def get_audios(self, order: AudioOrder = AudioOrder.PUBDATE, pn: int = 1):
        """
        获取用户投稿音频

        Args:
            order: 排序方式。默认：AudioOrder.PUBDATE
            pn: 页码数，从 1 开始。默认：1
        """
        api = API["info"]["audio"]
        params = {
            "uid": self.uid,
            "ps": 30,
            "pn": pn,
            "order": order.value
        }
        return await request("GET", url=api["url"], params=params, credential=self.credential)

    async def get_articles(self, pn: int = 1, order: ArticleOrder = ArticleOrder.PUBDATE):
        """
        获取用户投稿专栏

        Args:
            pn: 页码数，从 1 开始。默认：1
            order: 排序方式。默认：ArticleOrder.PUBDATE
        """
        api = API["info"]["article"]
        params = {
            "mid": self.uid,
            "ps": 30,
            "pn": pn,
            "sort": order.value
        }
        return await request("GET", url=api["url"], params=params, credential=self.credential)

    async def get_article_list(self, order: ArticleListOrder = ArticleListOrder.LATEST):
        """
        获取用户专栏文集

        Args:
            order: 排序方式。默认：ArticleListOrder.LATEST
        """
        api = API["info"]["article_lists"]
        params = {
            "mid": self.uid,
            "sort": order.value
        }
        return await request("GET", url=api["url"], params=params, credential=self.credential)

    @deprecated(reason="https://github.com/SocialSisterYi/bilibili-API-collect/issues/852")
    async def get_dynamics(self, offset: int = 0, need_top: bool = False):
        """
        获取用户动态

        Args:
            offset: 该值为第一次调用本方法时，数据中会有个 next_offset 字段，指向下一动态列表第一条动态（类似单向链表）。
                       根据上一次获取结果中的 next_offset 字段值，循环填充该值即可获取到全部动态。0 为从头开始。
                       默认：0
            need_top: 显示置顶动态。默认：False
        """
        api = API["info"]["dynamic"]
        params = {
            "host_uid": self.uid,
            "offset_dynamic_id": offset,
            "need_top": 1 if need_top else 0
        }
        data = await request("GET", url=api["url"], params=params, credential=self.credential)
        # card 字段自动转换成 JSON
        if 'cards' in data:
            for card in data["cards"]:
                card["card"] = json.loads(card["card"])
                card["extend_json"] = json.loads(card["extend_json"])
        return data

    async def get_subscribed_bangumis(self, pn: int = 1, type_: BangumiType = BangumiType.BANGUMI):
        """
        获取用户追番/追剧列表

        Args:
            pn: 页码数，从 1 开始。默认：1
            type_: 资源类型。默认：BangumiType.BANGUMI
        """
        api = API["info"]["bangumi"]
        params = {
            "vmid": self.uid,
            "pn": pn,
            "ps": 15,
            "type": type_.value
        }
        return await request("GET", url=api["url"], params=params, credential=self.credential)

    async def get_followings(self, pn: int = 1, desc: bool = True):
        """
        获取用户关注列表（不是自己只能访问前 5 页）

        Args:
            pn: 页码，从 1 开始。默认：1
            desc: 倒序排序。默认：True
        """
        api = API["info"]["followings"]
        params = {
            "vmid": self.uid,
            "ps": 100,
            "pn": pn,
            "order": "desc" if desc else "asc"
        }
        return await request("GET", url=api["url"], params=params, credential=self.credential)

    async def get_followers(self, pn: int = 1, desc: bool = True):
        """
        获取用户粉丝列表（不是自己只能访问前 5 页，是自己也不能获取全部的样子）

        Args:
            pn: 页码，从 1 开始。默认：1
            desc: 倒序排序。默认：True
        """
        api = API["info"]["followers"]
        params = {
            "vmid": self.uid,
            "ps": 20,
            "pn": pn,
            "order": "desc" if desc else "asc"
        }
        return await request("GET", url=api["url"], params=params, credential=self.credential)

    async def get_overview_stat(self):
        """
        获取用户的简易订阅和投稿信息
        """
        api = API["info"]["overview"]
        params = {
            "mid": self.uid,
            "jsonp": "jsonp"
        }
        return await request("GET", url=api["url"], params=params, credential=self.credential)

    # 操作用户
    async def modify_relation(self, relation: RelationType):
        """
        修改和用户的关系，比如拉黑、关注、取关等

        Args:
            relation: 操作类型
        """
        self.credential.raise_for_no_sessdata()
        self.credential.raise_for_no_bili_jct()

        api = API["operate"]["modify"]
        data = {
            "fid": self.uid,
            "act": relation.value,
            "re_src": 11
        }
        return await request("POST", url=api["url"], data=data, credential=self.credential)

    async def send_msg(self, text: str):
        """
        给用户发送私聊信息。目前仅支持纯文本

        Args:
            text: 信息内容
        """
        self.credential.raise_for_no_sessdata()
        self.credential.raise_for_no_bili_jct()

        api = API["operate"]["send_msg"]
        self_info = await self.__get_self_info()
        sender_uid = self_info["mid"]

        data = {
            "msg[sender_uid]": sender_uid,
            "msg[receiver_id]": self.uid,
            "msg[receiver_type]": 1,
            "msg[msg_type]": 1,
            "msg[msg_status]": 0,
            "msg[content]": json.dumps({"content": text}),
            "msg[dev_id]": "B9A37BF3-AA9D-4076-A4D3-366AC8C4C5DB",
            "msg[new_face_version]": "0",
            "msg[timestamp]": int(time.time()),
            "from_filework": 0,
            "build": 0,
            "mobi_app": "web"
        }
        return await request("POST", url=api["url"], data=data, credential=self.credential)


async def get_self_info(credential: Credential):
    """
    获取自己的信息

    Args:
        credential: 凭据
    """
    api = API["info"]["my_info"]
    credential.raise_for_no_sessdata()

    return await request("GET", api["url"], credential=credential)


async def create_subscribe_group(name: str, credential: Credential):
    """
    创建用户关注分组

    Args:
        name: 分组名
        credential: 凭据
    """
    credential.raise_for_no_sessdata()
    credential.raise_for_no_bili_jct()

    api = API["operate"]["create_subscribe_group"]
    data = {
        "tag": name
    }

    return await request("POST", api["url"], data=data, credential=credential)


async def delete_subscribe_group(group_id: int, credential: Credential):
    """
    删除用户关注分组

    Args:
        group_id: 分组 ID
        credential: 凭据
    """
    credential.raise_for_no_sessdata()
    credential.raise_for_no_bili_jct()

    api = API["operate"]["del_subscribe_group"]
    data = {
        "tagid": group_id
    }

    return await request("POST", api["url"], data=data, credential=credential)


async def rename_subscribe_group(group_id: int, new_name: str, credential: Credential):
    """
    重命名关注分组

    Args:
        group_id: 分组 ID
        new_name: 新的分组名
        credential: 凭据
    """
    credential.raise_for_no_sessdata()
    credential.raise_for_no_bili_jct()

    api = API["operate"]["rename_subscribe_group"]
    data = {
        "tagid": group_id,
        "name": new_name
    }

    return await request("POST", api["url"], data=data, credential=credential)


async def set_subscribe_group(uids: List[int], group_ids: List[int], credential: Credential):
    """
    设置用户关注分组

    Args:
        uids: 要设置的用户 UID 列表，必须已关注
        group_ids: 要复制到的分组列表
        credential: 凭据
    """
    credential.raise_for_no_sessdata()
    credential.raise_for_no_bili_jct()

    api = API["operate"]["set_user_subscribe_group"]
    data = {
        "fids": ",".join(map(lambda x: str(x), uids)),
        "tagids": ",".join(map(lambda x: str(x), group_ids))
    }

    return await request("POST", api["url"], data=data, credential=credential)


async def get_self_history(credential: Credential, page_num: int = 1, per_page_item: int = 100):
    """
    获取用户浏览历史记录

    Args:
        credential: 凭据
        page_num: 页码数。默认：1
        per_page_item: 每页多少条历史记录。默认：100
    """
    if not credential:
        credential = Credential()

    credential.raise_for_no_sessdata()

    api = API["info"]["history"]
    params = {
        "pn": page_num,
        "ps": per_page_item
    }

    return await request("GET", url=api["url"], params=params, credential=credential)
