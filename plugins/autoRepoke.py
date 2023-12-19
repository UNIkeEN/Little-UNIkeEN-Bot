from utils.basicEvent import send
from utils.standardPlugin import PokeStandardPlugin
from typing import Union, Any
from utils.bufferQueue import BufferQueue

class AutoRepoke(PokeStandardPlugin):
    def __init__(self, maxCapa:int=5) -> None:
        self.maxCapa = maxCapa
        self.bufferQueue = BufferQueue(3.0, maxCapa)
        self.bufferQueue.start()

    def judgeTrigger(self, data:Any)->bool:
        return data['target_id'] == data['self_id'] and data['sender_id'] != data['self_id']

    def pokeMessage(self, data:Any)->Union[None, str]:
        if len(self.bufferQueue) < self.maxCapa:
            self.bufferQueue.put(send, args=(data['group_id'], f"[CQ:poke,qq={data['sender_id']}]"))
        return "OK"