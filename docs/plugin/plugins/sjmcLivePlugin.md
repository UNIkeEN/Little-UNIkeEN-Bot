## 1. 插件简介

| 插件名称 | 父类 | 触发关键词 | 触发权限| 内容 |
| ---- | ---- | ---- | ---- | ---- |
| SjmcLiveStatus | StandardPlugin | '-mclive' / '-sjmclive' | None | 获取交大mc社B站直播状态，监测sjmc直播间信息，并在特定群广播开播消息 |
| FduMcLiveStatus | StandardPlugin | '-fdmclive' | None | 获取复旦基岩社B站直播状态，监测基岩社直播间信息，并在特定群广播开播消息 |

## 2. 示范样例

```bash
MC社B站未开播
111> -sjmclive
bot> 当前时段未开播哦

MC社B站开播
bot> 检测到MC社B站开播，SJMC社直播地址： https://live.bilibili.com/25567444
bot> 【sjmc直播间信息图片】
333> -sjmc
bot> 【sjmc直播间信息图片】
```

sjmc直播间信息图片:
![](../../images/plugins/sjmcLive.png) 

## 3. 代码分析

代码位于 plugins/sjmcLive.py

```python
class SjmcLiveStatus(StandardPlugin):
    monitorSemaphore = Semaphore()
    @staticmethod
    def dumpSjmcStatus(status: bool):
        exactPath = 'data/sjmcLive.json'
        with open(exactPath, 'w') as f:
            f.write('1' if status else '0')
    @staticmethod
    def loadSjmcStatus()->bool:
        exactPath = 'data/sjmcLive.json'
        with open(exactPath, 'r') as f:
            return f.read().startswith('1')
    def __init__(self) -> None:
        self.liveId = 25567444
        self.liveRoom = LiveRoom(self.liveId)
        self.timer = Timer(5, self.sjmcMonitor)
        if SjmcLiveStatus.monitorSemaphore.acquire(blocking=False):
            self.timer.start()
        self.exactPath = 'data/sjmcLive.json'
        self.prevStatus = False # false: 未开播, true: 开播
        self.sjmcQqGroup = 712514518
        if not os.path.isfile(self.exactPath):
            SjmcLiveStatus.dumpSjmcStatus(False)
        else:
            self.prevStatus = SjmcLiveStatus.loadSjmcStatus()
    def sjmcMonitor(self):
        # print('mctick')
        self.timer.cancel()
        self.timer = Timer(60,self.sjmcMonitor)
        self.timer.start()
        prevStatus = SjmcLiveStatus.loadSjmcStatus()
        roomInfo = asyncio.run(self.liveRoom.get_room_info())['room_info']
        currentStatus = roomInfo['live_status'] == 1
        if currentStatus != prevStatus:
            SjmcLiveStatus.dumpSjmcStatus(currentStatus)
            if currentStatus and self.sjmcQqGroup in getPluginEnabledGroups('sjmc'):
                send(self.sjmcQqGroup, '检测到MC社B站开播，SJMC社直播地址： https://live.bilibili.com/%d'%self.liveId)
                savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'sjmcLive.png')
                genLivePic(roomInfo, 'sjmc直播间状态', savePath)
                send(self.sjmcQqGroup, f'[CQ:image,file=files://{savePath},id=40000]')

    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg in ['-mclive', '-sjmclive']
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        try:
            roomInfo = asyncio.run(self.liveRoom.get_room_info())['room_info']
        except LiveException as e:
            warning("sjmc bilibili api exception: {}".format(e))
            return
        except ApiException as e:
            warning('bilibili api exception: {}'.format(e))
            return 
        except BaseException as e:
            warning('base exception in sjmclive: {}'.format(e))
            return
        if roomInfo['live_status'] == 1:
            savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'sjmcLive-%d.png'%target)
            genLivePic(roomInfo, 'sjmc直播间状态', savePath)
            send(target, f'[CQ:image,file=files://{savePath},id=40000]', data['message_type'])
        else:
            send(target, '当前时段未开播哦', data['message_type'])
        return "OK"
    def getPluginInfo(self) -> dict:
        return {
            'name': 'sjmclive',
            'description': '交大MC社B站直播间状态',
            'commandDescription': '-mclive/-sjmclive',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.3',
            'author': 'Unicorn',
        }
def genLivePic(roomInfo, title, savePath)->str:
    img = ResponseImage(
        theme = 'unicorn',
        title = title, 
        titleColor = PALETTE_SJTU_GREEN, 
        primaryColor = PALETTE_SJTU_RED, 
        footer = datetime.now().strftime('当前时间 %Y-%m-%d %H:%M:%S'),
        layout = 'normal'
    )
    img.addCard(
        ResponseImage.NoticeCard(
            title = roomInfo['title'],
            subtitle = datetime.fromtimestamp(roomInfo['live_start_time']).strftime(
                                                "开播时间  %Y-%m-%d %H:%M:%S"),
            keyword = '直播分区： '+roomInfo['area_name'],
            body = roomInfo['description'],
            illustration = roomInfo['keyframe'],
        )
    )
    img.generateImage(savePath)
    return savePath
```

为了确保实例化多个 `SjmcLiveStatus` 插件时只有一个监测广播mc社直播间状态，因此作者选用threading.Semaphore来保护监测线程入口