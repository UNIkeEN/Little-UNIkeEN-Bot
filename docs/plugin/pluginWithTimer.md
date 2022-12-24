# 1. 间隔固定时间触发插件

## 插件逻辑

间隔固定时间触发的插件推荐继承于 `CronStandardPlugin` 类，继承此类后，定时任务执行过程中所抛出的异常会被自动warning。

| 接口名称 | 参数 | 返回值类型 | 作用 |
| ---- | ---- | ---- | ---- |
| tick | - | `None` | 做每次触发任务所做的事情 |

# 2. 锚定固定时刻触发插件

TBD

# 代码分析

代码位于 `utils/standardPlugin.py`

```python
class CronStandardPlugin(ABC):
    def __init__(self) -> None:
        self.timer = None
        self.intervalTime = 180
    @abstractmethod
    def tick(self,)->None:
        """每次触发任务所做的事情"""
        raise NotImplementedError
    def _tick(self)->None:
        self.timer.cancel()
        self.timer = Timer(self.intervalTime, self._tick)
        self.timer.start()
        try:
            self.tick()
        except BaseException as e:
            warning('base exception in CronStandardPlugin: {}'.format(e))
    def start(self, startTime:float, intervalTime:float)->None:
        """开始执行
        @startTime: 从调用此函数开始过多久触发第一次任务，单位：秒
        @intervalTime: 间隔多久执行一次任务，单位：秒
        """
        self.timer = Timer(startTime, self._tick)
        self.intervalTime = intervalTime
        self.timer.start()
```