## 1. 插件简介

| 插件名称 | 父类 | 触发关键词 | 触发权限 | 内容 |
| ---- | ---- | ---- | ---- | ---- |
| AutoRepoke | PokeStandardPlugin | \[群内拍一拍消息\] | None | 回复拍一拍 |

!!! tip "设计初衷 —— 安全地回戳"
	在群聊中往往存在多个机器人，某机器人接收“戳@{..}”格式的消息会戳一戳被at的人，同时该机器人被戳时会自动回戳。如果Little-Unicorn-Bot是被 “戳@{..}” at的目标，那么Little-Unicorn-Bot和该机器人会不停地互戳，直到被腾讯限制。设计此插件的初衷就是为了安全地回戳。

## 2. 样例分析

```bash
111> 【戳一戳bot】
bot> 【戳一戳111】
```

## 3. 代码分析

代码位于 `plugins/autoRepoke.py`

```python
class AutoRepoke(PokeStandardPlugin):
    def __init__(self) -> None:
        self.mutex = Lock()
        self.fullResource = Semaphore(5)
        self.emptyResource = Semaphore(0)
        self.job = BaseTimeSchedulePlugin.scheduler.add_job(self._feedThread, 'interval', seconds=3)

    def _acquire(self)->bool:
        canPoke = False
        self.mutex.acquire(blocking=True)
        if self.fullResource.acquire(blocking=False):
            canPoke = True
            self.emptyResource.release()
        self.mutex.release()
        return canPoke
        
    def _release(self)->bool:
        result = False
        self.mutex.acquire(blocking=True)
        if self.emptyResource.acquire(blocking=False):
            self.fullResource.release()
            result = True
        self.mutex.release()
        return result

    def _feedThread(self):
        if not self._release():
            self.job.pause()
        
    def judgeTrigger(self, data:Any)->bool:
        return data['target_id'] == data['self_id']

    def pokeMessage(self, data:Any)->Union[None, str]:        
        if self._acquire():
            send(data['group_id'], f"[CQ:poke,qq={data['sender_id']}]")
            self.job.resume()
        return "OK"
```