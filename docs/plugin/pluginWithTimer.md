# 1. 间隔固定时间触发插件

## 插件逻辑

间隔固定时间触发的插件推荐继承于 `CronStandardPlugin` 类，继承此类后，定时任务执行过程中所抛出的异常会被自动warning。

| 接口名称 | 参数 | 返回值类型 | 作用 |
| ---- | ---- | ---- | ---- |
| tick | - | `None` | 做每次触发任务所做的事情 |
| start | _, intervalTime | `None` | 开始计时 |

!!! warning "注意：start接口首个参数弃用，留作占位符"
    由于历史原因，`CronStandardPlugin`类的`start`接口第一个参数"startTime"弃用

!!! warning "注意：CronStandardPlugin名称中的cron实际上对应apschedule的interval"
    由于历史原因，`CronStandardPlugin`类的"cron"实际上对应apschedule的"interval"


关于 `CronStandardPlugin` 类的使用，可参考:

- [B站订阅](./plugins/bilibiliSubscribePlugin.md) （轮询up主信息）
- [第二课堂](./plugins/sjtuDektPlugin.md) （轮询第二课堂信息）
- [SJTU教务处](./plugins/sjtuJwcPlugin.md) （轮询教务通知）
- [新闻](./plugins/newsPlugin.md) （轮询新闻更新信息）
- [SJMC直播间状态](./plugins/sjmcLivePlugin.md) （轮询SJMC直播间状态）
- [SJTU麦当劳](./plugins/sjtuMddPlugin.md) （轮询交大闵行麦当劳餐厅状态）

# 2. 锚定固定时刻触发插件

锚定固定时刻触发的插件推荐继承于 `ScheduleStandardPlugin` 类，继承此类后，定时任务执行过程中所抛出的异常会被自动warning。

| 接口名称 | 参数 | 返回值类型 | 作用 |
| ---- | ---- | ---- | ---- |
| tick | - | `None` | 做每次触发任务所做的事情 |
| schedule | hour, minute | `None` | 开始计时 |

!!! warning "注意：ScheduleStandardPlugin名称中的schedule实际上对应apschedule的cron"
    由于历史原因，`ScheduleStandardPlugin`类的"schedule"实际上对应apschedule的"cron"

关于 `ScheduleStandardPlugin` 类的使用，可参考：

- [昨日词云](./plugins/wordcloudPlugin.md) （每天0点定时更新词云）
- [彩票](./plugins/lotteryPlugin.md) （每天定时开奖）

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