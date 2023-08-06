## 缓冲队列简介

Little Unicorn Bot的缓冲队列基于操作系统课程中的“生产者-消费者”模型。在该模型中，有满和空两种资源，每种资源使用对应的信号量进行保护。生产者消耗空资源生产满资源，消费者消耗满资源生产空资源，满资源和空资源之和为定值（操作系统课上称之为盘子个数）。为了实现缓冲，我们只需将外部输入视为消费者，然后模拟生产者定时生产满资源，即可做到缓冲执行外部输入。

| 函数名 | 参数 | 返回值 | 功能 | 
| ---- | ---- | ---- | ---- |
| \_\_init\_\_ | `@feedInterval`: 生产者生产间隔（单位秒），`int`或`float`类型<br>`@maxCapa`: 满资源和空资源之和（须为正），`int`类型 | `None` | 初始化`bufferQueue`类 |
| put | `@func`: 待执行函数，`Callable`类型<br>`@args`: 待执行函数的args参数，`Tuple`类型<br>`@kwagrs`: 待执行函数的kwargs参数，`Dict`类型 | `None` | 设置缓冲队列执行对象 |
|start | - | `None` | 启动缓冲队列 |

## 应用场景分析

消息缓冲队列是缓冲队列最大的应用场景（此外还有拍一拍缓冲），代码如下（位于utils/basicEvent.py）：

```python
groupSendBufferQueue = BufferQueue(1, 1)
groupSendBufferQueue.start()
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
        groupSendBufferQueue.put(requests.get, (url,), {'params':params})
        # requests.get(url, params=params)
    elif type=='private':
        params = {
            "message_type": type,
            "user_id": id,
            "message": message
        }
        requests.get(url, params=params)
```

## 代码分析

代码位于 utils/bufferQueue.py

```python
class BufferQueue():
    def __init__(self, feedInterval:float, maxCapa:int) -> None:
        assert maxCapa > 0
        self.emptyResource = Semaphore(maxCapa)
        self.fullResource = Semaphore(0)
        self.queue = Queue()
        self.feedInterval = feedInterval
        self.feeder = Thread(target=self._feedThread)
        self.worker = Thread(target=self._workThread)

    def _acquire(self):
        self.emptyResource.acquire(blocking=True)
        func, args, kwargs = self.queue.get(block=True)
        func(*args, **kwargs)
        self.fullResource.release()
        
    def _release(self):
        self.fullResource.acquire(blocking=True)
        self.emptyResource.release()

    def _feedThread(self):
        while True:
            self._release()
            time.sleep(self.feedInterval)
    
    def _workThread(self):
        while True:
            self._acquire()

    def put(self, func:Callable, args:Tuple=(), kwargs:Dict[str, Any]={}):
        self.queue.put((func, args, kwargs), block=False)

    def start(self):
        self.feeder.start()
        self.worker.start()
```