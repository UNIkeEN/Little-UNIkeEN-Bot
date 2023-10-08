from threading import Timer, Semaphore, Lock, Thread
from queue import Queue
import time
from typing import Callable, Tuple, Any, Dict


class BufferQueue():
    def __init__(self, feedInterval: float, maxCapa: int) -> None:
        assert maxCapa > 0
        self.emptyResource = Semaphore(maxCapa)
        self.fullResource = Semaphore(0)
        self.queue = Queue()
        self.feedInterval = feedInterval
        self.feeder = Thread(target=self._feedThread)
        self.worker = Thread(target=self._workThread)
        self.feeder.daemon = True
        self.worker.daemon = True

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

    def put(self, func: Callable, args: Tuple = (), kwargs: Dict[str, Any] = {}):
        self.queue.put((func, args, kwargs), block=False)

    def start(self):
        self.feeder.start()
        self.worker.start()
