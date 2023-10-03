from typing import Tuple
from enum import IntEnum
from abc import ABC, abstractmethod, abstractstaticmethod

class BotProtocolType(IntEnum):
    UNKNOW = 0
    
    CONNECT = 100
    CONNECT_ON = 101
    CONNECT_OFF = 102
    
    STATUS = 110
    STATUS_QUERY = 111
    STATUS_REPLY = 112

class BotProtocolBase(ABC):
    @abstractmethod
    def getType(self)->BotProtocolType:
        raise NotImplementedError
    @abstractmethod
    def toStr(self) -> str:
        raise NotImplementedError
    @abstractstaticmethod
    def fromStr(text:str)->"BotProtocolBase":
        raise NotImplementedError

def parseProtocolHead(protocolHead:str)->Tuple[bool, str]:
    line0 =protocolHead.strip().split()
    if len(line0) != 2 or line0[0] != 'LUB_NET_PROTOCOL':
        return False, 'Head Error'
    if not line0[1].isdigit() or int(line0[1]) > 1:
        return False, 'Version Error'
    return True, line0[1]

def protocolClassification(text:str)->BotProtocolType:
    if not text.startswith('LUB_NET_PROTOCOL'):
        return BotProtocolType.UNKNOW
    lines = text.strip().split('\n')
    if len(lines) < 2:
        return BotProtocolType.UNKNOW
    protocolType = lines[1].strip().split()
    if len(protocolType) != 2:
        return BotProtocolType.UNKNOW
    if protocolType[0] == 'CONNECT':
        if protocolType[1] == 'ON':
            return BotProtocolType.CONNECT_ON
        elif protocolType[1] == 'OFF':
            return BotProtocolType.CONNECT_OFF
        else:
            return BotProtocolType.UNKNOW
    elif protocolType[0] == 'STATUS':
        if protocolType[1] == 'QUERY':
            return BotProtocolType.STATUS_QUERY
        elif protocolType[1] == 'REPLY':
            return BotProtocolType.STATUS_REPLY
        else:
            return BotProtocolType.UNKNOW
    else:
        BotProtocolType.UNKNOW