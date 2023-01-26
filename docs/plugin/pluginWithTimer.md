# 1. 间隔固定时间触发插件

## 插件逻辑

间隔固定时间触发的插件推荐继承于 `CronStandardPlugin` 类，继承此类后，定时任务执行过程中所抛出的异常会被自动warning。

| 接口名称 | 参数 | 返回值类型 | 作用 |
| ---- | ---- | ---- | ---- |
| tick | - | `None` | 做每次触发任务所做的事情 |
| start | _, intervalTime | `None` | 开始计时 |

# 2. 锚定固定时刻触发插件

锚定固定时刻触发的插件推荐继承于 `ScheduleStandardPlugin` 类，继承此类后，定时任务执行过程中所抛出的异常会被自动warning。

| 接口名称 | 参数 | 返回值类型 | 作用 |
| ---- | ---- | ---- | ---- |
| tick | - | `None` | 做每次触发任务所做的事情 |
| schedule | hour, minute | `None` | 开始计时 |

# 代码分析

代码位于 `utils/standardPlugin.py`

```python
class BaseTimeSchedulePlugin(ABC):
    """定时任务基类，参考apscheduler文档"""
    scheduler = BackgroundScheduler()
    scheduler.start()

    @abstractmethod
    def tick(self,)->None:
        """每次触发任务所做的事情"""
        raise NotImplementedError
    
    @final
    def _tick(self,)->None:
        try:
            self.tick()
        except BaseException as e:
            warning('exception in ScheduleStandardPlugin: {}'.format(e))

class ScheduleStandardPlugin(BaseTimeSchedulePlugin):
    """固定每日时刻执行"""
    def schedule(self, hour:Union[str, int]=0, minute:Union[str, int]=0)->None:
        """可以重写此方法
        @hour: 
        @minute:
        e.g:
            hour: (str)'1-3', minute: None ---- 每天 1:00, 2:00, 3:00 运行
            hour: (int)0, minute: (int)1   ---- 每天 0:01 运行
        """
        BaseTimeSchedulePlugin.scheduler.add_job(self._tick, 'cron', hour=hour, minute=minute)

class CronStandardPlugin(BaseTimeSchedulePlugin):
    """间隔固定时长执行"""
    def start(self, startTime:float, intervalTime:float)->None:
        """开始执行，可以重写此方法
        @startTime: deprecated
        @intervalTime: 间隔多久执行一次任务，单位：秒
        """
        BaseTimeSchedulePlugin.scheduler.add_job(self._tick, 'interval', seconds=intervalTime)

```