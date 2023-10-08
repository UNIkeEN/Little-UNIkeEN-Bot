from utils.basic_event import send
from utils.standard_plugin import PokeStandardPlugin
from typing import Union, Any
from utils.buffer_queue import BufferQueue

class AutoRepoke(PokeStandardPlugin):
    def __init__(self) -> None:
        self.bufferQueue = BufferQueue(3.0, 5)
        self.bufferQueue.start()

    def judgeTrigger(self, data:Any)->bool:
        return data['target_id'] == data['self_id']

    def pokeMessage(self, data:Any)->Union[None, str]:        
        self.bufferQueue.put(send, args=(data['group_id'], f"[CQ:poke,qq={data['sender_id']}]"))
        return "OK"