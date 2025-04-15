import ssl
from typing import Callable, Optional

import websockets
import websockets.legacy.client

from utils.basicEvent import warning

from .common.packets import *
from .common.subprotocols import *


class Client:
    def __init__(self, id:str, token:str, server:str):
        self.ws:Optional[websockets.legacy.client.Connect] = None
        self.id:str = id
        self.token:str = token
        self.server:str = server
        self.handle_payload_fn:Optional[Callable[[str,str],None]] = None
        
    def reset_credential(self, id:str, token:str, server:str)->None:
        self.id:str = id
        self.token:str = token
        self.server:str = server
        
    def set_handle_payload_fn(self, payload_fn:Callable)->None:
        self.handle_payload_fn = payload_fn

    async def send_payload(self, payload : PayloadPacket):
        print('-------------------')
        print(payload.to_json())
        print('-------------------')
        await self.ws.send(payload.to_json())

    async def handle_payload(self, payload : PayloadPacket)->None:
        sessionId = payload.get_session_id()
        if self.handle_payload_fn != None:
            try:
                self.handle_payload_fn(sessionId, payload)
            except BaseException as e:
                warning(f'exception in handling mua payload: {e}, payload: {str(payload)}')
        else:
            print("[WARNING]: handle_payload_fn is None")
            
    async def send_packet(self, packet : Packet)->None:
        await self.ws.send(packet.to_json())

    async def authenticate(self)->bool:
        await self.send_packet(ClientAuthPacket.default_auth_type(self.id, self.token))
        packet = await self.ws.recv()
        auth_result = Packet.from_json(packet)
        if isinstance(auth_result, ErrorPacket):
            print("[ERROR] Authentication failure. ", auth_result.error_info)
            return False
        return True

    async def event_loop(self)->None:
        async for packet in self.ws:
            payload = Packet.from_json(packet)
            if not isinstance(payload, PayloadPacket):
                print("[ERROR] Received unknown packet!")
                continue
            await self.handle_payload(payload)
            
    async def connect(self)->None:
        self.ws = await websockets.connect(self.server, ssl=ssl.SSLContext())