# bilibili-api-python: version 15.5.1
# remove session pool to avoid too many CLOSE_WAIT
from bilibili_api.utils.network_httpx import *
from bilibili_api.user import User, VideoOrder
from bilibili_api.user import API as API_USER
from bilibili_api.live import LiveRoom
from bilibili_api.live import API as API_LIVE


@dataclass
class ApiFixed:
    url: str
    method: str
    comment: str = ""
    wbi: bool = False
    verify: bool = False
    no_csrf: bool = False
    json_body: bool = False
    ignore_code: bool = False
    data: dict = field(default_factory=dict)
    params: dict = field(default_factory=dict)
    credential: Credential = field(default_factory=Credential)
    """
    用于请求的 Api 类

    Args:
        url (str): 请求地址

        method (str): 请求方法

        comment (str, optional): 注释. Defaults to "".

        wbi (bool, optional): 是否使用 wbi 鉴权. Defaults to False.

        verify (bool, optional): 是否验证凭据. Defaults to False.

        no_csrf (bool, optional): 是否不使用 csrf. Defaults to False.

        json_body (bool, optional): 是否使用 json 作为载荷. Defaults to False.

        ignore_code (bool, optional): 是否忽略返回值 code. Defaults to False.

        data (dict, optional): 请求载荷. Defaults to {}.

        params (dict, optional): 请求参数. Defaults to {}.

        credential (Credential, optional): 凭据. Defaults to Credential().
    """

    def __post_init__(self):
        self.method = self.method.upper()
        self.original_data = self.data.copy()
        self.original_params = self.params.copy()
        self.data = {k: "" for k in self.data.keys()}
        self.params = {k: "" for k in self.params.keys()}
        if self.credential is None:
            self.credential = Credential()
        self.__result = None

    def __setattr__(self, __name: str, __value: Any) -> None:
        """
        每次更新参数都要把 __result 清除
        """
        if self.initialized and __name != "_Api__result":
            self.__result = None
        return super().__setattr__(__name, __value)

    @property
    def initialized(self):
        return "_Api__result" in self.__dict__

    @property
    def result(self) -> Union[None, dict]:
        """
        异步获取请求结果

        `self.__result` 用来暂存数据 参数不变时获取结果不变
        """
        if self.__result is None:
            self.__result = request_fixed(self)
        return self.__result

    @property
    def sync_result(self) -> Union[None, dict]:
        """
        通过 `sync` 同步获取请求结果

        一般用于非协程内同步获取数据
        """
        return self.result

    @property
    def thread_result(self) -> Union[None, dict]:
        """
        通过 `threading.Thread` 同步获取请求结果

        一般用于协程内同步获取数据

        为什么协程里不直接 await self.result 呢

        因为协程内有的地方不让异步

        例如类的 `__init__()` 函数中需要获取请求结果时
        """
        job = threading.Thread(target=asyncio.run, args=[self.result])
        job.start()
        while job.is_alive():
            time.sleep(0.0167)
        return self.__result

    def update_data(self, **kwargs):
        """
        毫无亮点的更新 data
        """
        self.data.update(kwargs)
        self.__result = None
        return self

    def update_params(self, **kwargs):
        """
        毫无亮点的更新 params
        """
        self.params.update(kwargs)
        self.__result = None
        return self

    def update(self, **kwargs):
        """
        毫无亮点的自动选择更新
        """
        if self.method == "GET":
            return self.update_params(**kwargs)
        else:
            return self.update_data(**kwargs)

    @classmethod
    def from_file(cls, path: str, credential: Union[Credential, None] = None):
        """
        以 json 文件生成对象

        Args:
            path (str): 例如 user.info.info
            credential (Credential, Optional): 凭据类. Defaults to None.

        Returns:
            api (Api): 从文件中读取的 api 信息
        """
        path_list = path.split(".")
        api = get_api(path_list.pop(0))
        for key in path_list:
            api = api.get(key)
        return cls(credential=credential, **api)


def get_nav_fixed(credential: Union[Credential, None] = None):
    """
    获取导航

    Args:
        credential (Credential, Optional): 凭据类. Defaults to None

    Returns:
        dict: 账号相关信息
    """
    return ApiFixed(credential=credential, **get_api("credential")["info"]["valid"]).result


def get_mixin_key_fixed() -> str:
    """
    获取混合密钥

    Returns:
        str: 新获取的密钥
    """
    data = get_nav_fixed()
    wbi_img: Dict[str, str] = data["wbi_img"]

    def split(key): return wbi_img.get(key).split("/")[-1].split(".")[0]

    ae = split("img_url") + split("sub_url")
    oe = [46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12,
          38, 41, 13,
          37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20,
          34, 44, 52]
    le = reduce(lambda s, i: s + (ae[i] if i < len(ae) else ""), oe, "")
    return le[:32]


def rollback_fixed(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AttributeError:
            return request_old_fixed(*args, **kwargs)

    return wrapper


@rollback_fixed
def request_fixed(api: Api, url: str = "", params: dict = None, **kwargs) -> Any:
    """
    向接口发送请求。

    Args:
        api (Api): 请求 Api 信息。

        url, params: 这两个参数是为了通过 Conventional Commits 写的，最后使用的时候(指完全取代老的之后)可以去掉。

    Returns:
        接口未返回数据时，返回 None，否则返回该接口提供的 data 或 result 字段的数据。
    """
    # 请求为非 GET 且 no_csrf 不为 True 时要求 bili_jct
    if api.method != "GET" and not api.no_csrf:
        api.credential.raise_for_no_bili_jct()

    if settings.request_log:
        settings.logger.info(api)

    # jsonp
    if api.params.get("jsonp") == "jsonp":
        api.params["callback"] = "callback"

    if api.wbi:
        global wbi_mixin_key
        if wbi_mixin_key == "":
            wbi_mixin_key = get_mixin_key_fixed()
        enc_wbi(api.params, wbi_mixin_key)

    # 自动添加 csrf
    if not api.no_csrf and api.method in ["POST", "DELETE", "PATCH"]:
        api.data["csrf"] = api.credential.bili_jct
        api.data["csrf_token"] = api.credential.bili_jct

    cookies = api.credential.get_cookies()
    cookies["buvid3"] = str(uuid.uuid1())
    cookies["Domain"] = ".bilibili.com"

    config = {
        "url": api.url,
        "method": api.method,
        "data": api.data,
        "params": api.params,
        "cookies": cookies,
        "headers": HEADERS.copy(),
    }
    config.update(kwargs)

    if api.json_body:
        config["headers"]["Content-Type"] = "application/json"
        config["data"] = json.dumps(config["data"])

    resp = httpx.request(**config)

    # 检查响应头 Content-Length
    content_length = resp.headers.get("content-length")
    if content_length and int(content_length) == 0:
        return None

    if "callback" in api.params:
        # JSONP 请求
        resp_data: dict = json.loads(
            re.match("^.*?({.*}).*$", resp.text, re.S).group(1))
    else:
        # JSON
        resp_data: dict = json.loads(resp.text)

    # 检查 code
    if not api.ignore_code:
        code = resp_data.get("code")

        if code is None:
            raise ResponseCodeException(-1, "API 返回数据未含 code 字段", resp_data)
        if code != 0:
            msg = resp_data.get("msg")
            if msg is None:
                msg = resp_data.get("message")
            if msg is None:
                msg = "接口未返回错误信息"
            raise ResponseCodeException(code, msg, resp_data)

    real_data = resp_data.get("data")
    if real_data is None:
        real_data = resp_data.get("result")
    return real_data


def request_old_fixed(
        method: str,
        url: str,
        params: Union[dict, None] = None,
        data: Any = None,
        credential: Union[Credential, None] = None,
        no_csrf: bool = False,
        json_body: bool = False,
        **kwargs,
) -> Any:
    """
    向接口发送请求。

    Args:
        method     (str)                 : 请求方法。

        url        (str)                 : 请求 URL。

        params     (dict, optional)      : 请求参数。

        data       (Any, optional)       : 请求载荷。

        credential (Credential, optional): Credential 类。

        no_csrf    (bool, optional)      : 不要自动添加 CSRF。

        json_body  (bool, optional)      : 载荷是否为 JSON

    Returns:
        接口未返回数据时，返回 None，否则返回该接口提供的 data 或 result 字段的数据。
    """
    if credential is None:
        credential = Credential()

    method = method.upper()
    # 请求为非 GET 且 no_csrf 不为 True 时要求 bili_jct
    if method != "GET" and not no_csrf:
        credential.raise_for_no_bili_jct()

    # 使用 Referer 和 UA 请求头以绕过反爬虫机制
    # DEFAULT_HEADERS = {
    #     "Referer": "https://www.bilibili.com",
    #     "User-Agent": "Mozilla/5.0",
    # }
    # 现有常量为啥不用...
    headers = HEADERS.copy()

    if params is None:
        params = {}

    # 处理 wbi 鉴权
    # 为什么tmd api 信息不传入而是直接传入 url
    if "wbi" in url:  # 只能暂时这么判断了
        global wbi_mixin_key
        if wbi_mixin_key == "":
            wbi_mixin_key = get_mixin_key_fixed()
        enc_wbi(params, wbi_mixin_key)

    # 自动添加 csrf
    if not no_csrf and method in ["POST", "DELETE", "PATCH"]:
        if data is None:
            data = {}
        data["csrf"] = credential.bili_jct
        data["csrf_token"] = credential.bili_jct

    # jsonp

    if params.get("jsonp", "") == "jsonp":
        params["callback"] = "callback"

    cookies = credential.get_cookies()
    cookies["buvid3"] = str(uuid.uuid1())
    cookies["Domain"] = ".bilibili.com"

    config = {
        "method": method,
        "url": url,
        "params": params,
        "data": data,
        "headers": headers,
        "cookies": cookies,
    }

    config.update(kwargs)

    if json_body:
        config["headers"]["Content-Type"] = "application/json"
        config["data"] = json.dumps(config["data"])

    # config["ssl"] = False

    # config["verify_ssl"] = False
    # config["ssl"] = False

    if True:  # try:
        resp = httpx.request(**config)
    # except Exception :
    #    raise httpx.ConnectError("连接出错。")

    # 检查响应头 Content-Length
    content_length = resp.headers.get("content-length")
    if content_length and int(content_length) == 0:
        return None

    # 检查响应头 Content-Type
    content_type = resp.headers.get("content-type")

    # 不是 application/json
    # if content_type.lower().index("application/json") == -1:
    #     raise ResponseException("响应不是 application/json 类型")

    raw_data = resp.text
    resp_data: dict

    if "callback" in params:
        # JSONP 请求
        resp_data = json.loads(
            re.match("^.*?({.*}).*$", raw_data, re.S).group(1))  # type: ignore
    else:
        # JSON
        resp_data = json.loads(raw_data)

    # 检查 code
    code = resp_data.get("code", None)

    if code is None:
        raise ResponseCodeException(-1, "API 返回数据未含 code 字段", resp_data)
    if code != 0:
        msg = resp_data.get("msg", None)
        if msg is None:
            msg = resp_data.get("message", None)
        if msg is None:
            msg = "接口未返回错误信息"
        raise ResponseCodeException(code, msg, resp_data)

    real_data = resp_data.get("data", None)
    if real_data is None:
        real_data = resp_data.get("result", None)
    return real_data


class LiveRoomFixed(LiveRoom):
    # def __init__(self, *args, **kwargs):
    #     super(LiveRoom, self).__init__(*args, **kwargs)
    def get_room_info(self):
        api = API_LIVE["info"]["room_info"]
        params = {"room_id": self.room_display_id}
        return request_fixed(
            api["method"], api["url"], params, credential=self.credential
        )


class UserFixed(User):
    def __init__(self, uid: int, credential: Union[Credential, None] = None):
        super(UserFixed, self).__init__(uid, credential)

    def get_user_info(self) -> dict:
        api = API_USER["info"]["info"]
        params = {
            "mid": self.get_uid(),
        }
        return request_fixed(
            "GET", url=api["url"], params=params, credential=self.credential
        )

    def get_videos(
            self,
            tid: int = 0,
            pn: int = 1,
            ps: int = 30,
            keyword: str = "",
            order: VideoOrder = VideoOrder.PUBDATE,
    ) -> dict:
        api = API_USER["info"]["video"]
        params = {
            "mid": self.get_uid(),
            "ps": ps,
            "tid": tid,
            "pn": pn,
            "keyword": keyword,
            "order": order.value,
        }
        return request_fixed(
            "GET", url=api["url"], params=params, credential=self.credential
        )

    def get_dynamics(self, offset: int = 0, need_top: bool = False) -> dict:
        """
        获取用户动态。

        Args:
            offset (str, optional):     该值为第一次调用本方法时，数据中会有个 next_offset 字段，

                                        指向下一动态列表第一条动态（类似单向链表）。

                                        根据上一次获取结果中的 next_offset 字段值，

                                        循环填充该值即可获取到全部动态。

                                        0 为从头开始。
                                        Defaults to 0.

            need_top (bool, optional):  显示置顶动态. Defaults to False.

        Returns:
            dict: 调用接口返回的内容。
        """
        api = API_USER["info"]["dynamic"]
        params = {
            "host_uid": self.get_uid(),
            "offset_dynamic_id": offset,
            "need_top": 1 if need_top else 0,
        }
        data = request_fixed(
            "GET", url=api["url"], params=params, credential=self.credential
        )
        # card 字段自动转换成 JSON。
        if "cards" in data:
            for card in data["cards"]:
                card["card"] = json.loads(card["card"])
                card["extend_json"] = json.loads(card["extend_json"])
        return data


if __name__ == '__main__':
    liveRoom = LiveRoomFixed(24716629)
    print(liveRoom.get_room_info())
    user = UserFixed(29440965)
    print(user.get_user_info())
