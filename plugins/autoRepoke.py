from utils.basicEvent import send
from utils.standardPlugin import PokeStandardPlugin, BaseTimeSchedulePlugin
from threading import Semaphore, Lock
from typing import Union, Any

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