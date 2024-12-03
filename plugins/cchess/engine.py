import subprocess, io
from abc import ABC, abstractmethod
import re
import os
from typing import List, Dict, Optional
import enum
from .move import Move

class EngineError(Exception):
    pass

class EngineState(enum.IntEnum):
    DOWN = 0
    INIT = 1
    READY = 2
    THINKING = 3
    
class Engine(ABC):
    def __init__(self, engine_path: str):
        self.engine_path = engine_path
        self.state = EngineState.DOWN
        self.stdin:Optional[io.IOBase] = None
        self.stdout:Optional[io.IOBase] = None
        
    def open(self):
        if self.state != EngineState.DOWN:
            raise EngineError("call Engine.open while Engine.state is not 'DOWN'")
        if not os.path.isfile(self.engine_path):
            raise EngineError("找不到UCCI引擎！")
        self._process = subprocess.Popen(
            args=[self.engine_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        self.stdin = self._process.stdin
        self.stdout = self._process.stdout
        self.start()
        self.state = EngineState.INIT

    def close(self):
        if self.state == EngineState.DOWN:
            raise EngineError("call Engine.close while Engine.state is 'DOWN'")
        self.stop()
        self._process.kill()
        self.state = EngineState.DOWN
        self.stdin = None
        self.stdout = None

    def send_line(self, line: str):
        if self.stdin is None:
            raise EngineError("stdin is None when called Engine.send_line")
        self.stdin.write(f"{line}\r\n".encode("utf-8"))
        self.stdin.flush()

    def read_line(self) -> str:
        if self.stdout is None:
            raise EngineError("stdout is None when called Engine.read_line")
        line = self.stdout.readline()
        return line.decode("utf-8").strip()

    def read_lines(self, endword: str) -> List[str]:
        lines = []
        while True:
            line = self.read_line()
            lines.append(line)
            if line.startswith(endword):
                break
        return lines

    def make_ready(self) -> bool:
        if self.state == EngineState.DOWN:
            raise EngineError("call Engine.make_ready while Engine.state is 'DOWN'")
        if self.state == EngineState.THINKING:
            raise EngineError("call Engine.make_ready while Engine.state is 'THINKING'")
        self.send_line('isready')
        lines = self.read_lines('readyok')
        if len(lines) > 0:
            self.state = EngineState.READY
            return True
        return False
    
    @abstractmethod
    def start(self):
        raise NotImplementedError()

    @abstractmethod
    def stop(self):
        raise NotImplementedError()

    def bestmove(self, position: str, time: int = 10_000, depth: int = 25) -> Move:
        """根据当前状态获取下一步最佳着法
        * `position`: 设置棋盘局面的字符串，形式为 `position fen <FEN> moves <MOVES>`
        * `time`: 限定搜索时间，单位为毫秒
        * `depth`: 限定搜索深度
        """
        if self.state != EngineState.READY:
            raise EngineError("call Engine.bestmove while Engine.state is not 'READY'")
        self.state = EngineState.THINKING
        self.send_line(position)
        self.send_line(f"go time {time} depth {depth}")
        lines = self.read_lines("bestmove")
        if not lines:
            raise EngineError("引擎无法获取合适的着法")
        match = re.search(r"bestmove ([a-zA-Z]\d[a-zA-Z]\d)", lines[-1])
        if not match:
            raise EngineError("引擎返回的结果形式不正确")
        self.state = EngineState.READY
        return Move.from_ucci(match.group(1))

    def set_options(self, options: Dict[str, str]):
        for k, v in options.items():
            self.send_line("setoption name %s value %s"%(k, v))

class UcciEngine(Engine):
    def start(self):
        self.send_line("ucci")
        self.read_lines("ucciok")
    def stop(self):
        self.send_line("quit")
    
class UciEngine(Engine):
    def start(self):
        self.send_line("uci")
        self.read_lines("uciok")
    def stop(self):
        self.send_line("quit")
        