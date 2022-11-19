## 1. 插件简介

| 插件名称 | 父类 | 触发关键词 | 触发权限 | 内容 |
| ---- | ---- | ---- | ---- | ---- |
| Show2cyPIC | StandardPlugin | '来点图图' | None | 获取二次元图片 |
| ShowSePIC | StandardPlugin | '来点涩涩' | None | 获取二次元大尺度图片 |

!!! warning "风险提示"
    注意：触发 ShowSePIC 插件后 bot 大概率会被风控

## 2. 示范样例

```bash
111> 来点图图
bot> 【二次元图片】
222> 来点涩涩
bot> 【二次元大尺度图片】
```

## 3. 代码分析

代码位于 plugins/show2cyPic.py

```python
class Show2cyPIC(StandardPlugin): 
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg == '来点图图'
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        req = requests.get(url='https://tenapi.cn/acg',params={'return': 'json'})
        if req.status_code != requests.codes.ok:
            warning("tenapi failed in Show2cyPIC")
            return "OK"
        try:
            pic_url = req.json()['imgurl']
        except requests.JSONDecodeError as e:
            warning("json decode error in Show2cyPIC: {}".format(e))
            return "OK"
        except KeyError as e:
            warning("key error in Show2cyPIC: {}".format(e))
            return "OK"
        send(target,'[CQ:image,file=' + pic_url + ']', data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'Show2cyPIC',
            'description': '来点图图',
            'commandDescription': '来点图图',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
class ShowSePIC(StandardPlugin): 
    def __init__(self) -> None:
        print('注意，开启ShowSePIC插件有被腾讯封号的危险')
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return startswith_in(msg, ['来点涩涩'])
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        msg_split = msg.split()
        if len(msg_split)==0:
            tag=''
        else:
            tag=msg.replace('来点涩涩','',1)
            tag=tag.strip().split()
            tagText = ""
            for t in tag:
                tagText += urllib.parse.quote(t) + '|'
            tagText = tagText[:-1]
            try:
                req= requests.get(url=f"https://api.lolicon.app/setu/v2?tag={tagText}&r18=0&size=regular",params={'return': 'json'})
                if req.status_code != requests.codes.ok:
                    warning("lolicon API failed in ShowSePIC")
                    return "OK"
                pic_url = req.json()['data'][0]['urls']['regular']
                target = data['group_id'] if data['message_type']=='group' else data['user_id']
                send(target,'[CQ:image,file=' + pic_url + ',type=flash]',data['message_type'])
            except BaseException as e:
                warning('exception in show2cyPic, error: {}'.format(e))
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'ShowSePIC',
            'description': '来点涩涩',
            'commandDescription': '来点涩涩 [tag]',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
```