驱动器对接包含各类与go-cqhttp交互的函数。

其中最重要的即发送信息的函数 `send` ，参数信息如下：

<table>
    <tr>
          <th>参数名称</th>
          <th>描述</th>
          <th>取值</th>
          <th>取值说明</th>
          <th>备注</th>
	</tr>
    <tr>
          <td>id</td>
          <td>保存地址</td>
          <td>int型变量</td>
          <td>表示要发送的群号或者对象qq号</td>
          <td></td>
    </tr>
    <tr>
          <td>message</td>
          <td>消息</td>
          <td>str型变量</td>
          <td>表示要发送的消息</td>
          <td>如要发送图片、音频、表情、文件等，请使用<a href="https://docs.go-cqhttp.org/cqcode/#%E8%BD%AC%E4%B9%89">cq码转义</a></td>
    </tr>
    <tr>
          <td>type</td>
          <td>类型</td>
          <td>str型变量</td>
          <td>表示要发送的消息类型</td>
          <td>群聊-'group'；私聊-'private'</td>
    </tr>
</table>

关于其他对接函数即功能（如获取群聊列表，获取群聊历史记录），请参见下方代码分析：

## 代码分析

```python
def send(id: int, message: str, type:str='group')->None:
    """发送消息
    id: 群号或者私聊对象qq号
    message: 消息
    type: Union['group', 'private'], 默认 'group'
    """
    url = HTTP_URL+"/send_msg"
    if type=='group':
        params = {
            "message_type": type,
            "group_id": id,
            "message": message
        }
        print(params)
        requests.get(url, params=params)
    elif type=='private':
        params = {
            "message_type": type,
            "user_id": id,
            "message": message
        }
        print(params)
        requests.get(url, params=params)

def get_group_list()->list:
    """获取群聊列表
    @return:
        [
            {
                'group_create_time': int,
                'group_id': int,
                'group_name': str,
                'group_level': int,
                'max_member_count': int,
                'member_count': int,
            },
            ....
        ]
    参考链接： https://docs.go-cqhttp.org/api/#%E8%8E%B7%E5%8F%96%E7%BE%A4%E5%88%97%E8%A1%A8
    """
    url = HTTP_URL+"/get_group_list"
    try:
        groupList = json.loads(requests.get(url).text)
        if groupList['status'] != 'ok':
            warning("get_group_list requests not return ok")
            return []
        return groupList['data']
    except BaseException as e:
        warning("error in get_group_list, error: {}".format(e))
        return []

def get_group_msg_history(group_id: int, message_seq: Union[int, None]=None)->list:
    """获取群消息历史记录
    @message_seq:
        起始消息序号, 可通过 get_msg 获得
        如果是None将默认获取最新的消息
    @group_id: 群号
    @return: 从起始序号开始的前19条消息
    参考链接： https://docs.go-cqhttp.org/api/#%E8%8E%B7%E5%8F%96%E7%BE%A4%E6%B6%88%E6%81%AF%E5%8E%86%E5%8F%B2%E8%AE%B0%E5%BD%95
    """
    url = HTTP_URL+"/get_group_msg_history"
    try:
        params = {
            "group_id": group_id
        }
        if message_seq != None:
            params["message_seq"] = message_seq
            
        messageHistory = json.loads(requests.get(url, params=params).text)
        if messageHistory['status'] != 'ok':
            if messageHistory['msg'] == 'MESSAGES_API_ERROR':
                print("group {} meet message API error".format(group_id))
            else:
                warning("get_group_msg_history requests not return ok\nmessages = {}\ngroup_id={}\nmessage_seq={}".format(
                messageHistory, group_id, message_seq))
            return []
        return messageHistory['data']['messages']
    except BaseException as e:
        warning('error in get_group_msg_history, error: [}'.format(e))
        return []
def get_essence_msg_list(group_id: int)->list:
    """获取精华消息列表
    @group_id:  群号
    @return:    精华消息列表
    """
    url = HTTP_URL+"/get_essence_msg_list"
    try:
        params = {
            "group_id": group_id
        }
        essenceMsgs = json.loads(requests.get(url, params=params).text)
        if essenceMsgs['status'] != 'ok':
            warning("get_essence_msg_list requests not return ok")
            return []
        return essenceMsgs['data']
    except BaseException as e:
        warning("error in get_essence_msg_list, error: {}".format(e))
        return []
def set_friend_add_request(flag, approve=True)->None:
    """处理加好友"""
    url = HTTP_URL+"/set_friend_add_request"
    params = {
        "flag": flag,
        "approve": approve
    }
    print(params)
    requests.get(url, params=params)

```