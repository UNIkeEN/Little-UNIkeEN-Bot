from typing import Any, Union

from utils.basicEvent import send
from utils.bufferQueue import BufferQueue
from utils.standardPlugin import PokeStandardPlugin


class AutoRepoke(PokeStandardPlugin):
    def __init__(self, maxCapa:int=5) -> None:
        self.maxCapa = maxCapa
        self.bufferQueue = BufferQueue(3.0, maxCapa)
        self.bufferQueue.start()

    def judgeTrigger(self, data:Any)->bool:
        return data['target_id'] == data['self_id'] and data['user_id'] != data['self_id']

    def pokeMessage(self, data:Any)->Union[None, str]:
        return # TODO
        if len(self.bufferQueue) < self.maxCapa:
            self.bufferQueue.put(send, args=(data['group_id'], f"[CQ:poke,sub_type=poke,target_id={data['user_id']},qq={data['user_id']}]"))
        return "OK"