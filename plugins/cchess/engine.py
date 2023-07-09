import asyncio
import re
from pathlib import Path
from typing import List

from .move import Move


class EngineError(Exception):
    pass


class UCCIEngine:
    def __init__(self, engine_path: Path):
        self.engine_path = engine_path.resolve()

    async def open(self):
        if not self.engine_path.exists():
            raise EngineError("找不到UCCI引擎！")
        self._process = await asyncio.create_subprocess_exec(
            program=str(self.engine_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self.stdin = self._process.stdin
        self.stdout = self._process.stdout
        await self.start()

    def close(self):
        self.stop()
        self._process.kill()

    def send_line(self, line: str):
        assert self.stdin is not None
        self.stdin.write(f"{line}\n".encode("utf-8"))

    async def read_line(self, timeout: int = 10) -> str:
        assert self.stdout is not None
        try:
            line = await asyncio.wait_for(self.stdout.readline(), timeout)
        except asyncio.TimeoutError:
            raise EngineError("读取引擎输出超时")
        return line.decode("utf-8").strip()

    async def read_lines(self, endword: str) -> List[str]:
        lines = []
        while True:
            line = await self.read_line()
            lines.append(line)
            if line.startswith(endword):
                break
        return lines

    async def start(self):
        self.send_line("ucci")
        await self.read_lines("ucciok")

    def stop(self):
        self.send_line("quit")

    async def bestmove(self, position: str, time: int = 500, depth: int = 10) -> Move:
        """根据当前状态获取下一步最佳着法
        * `position`: 设置棋盘局面的字符串，形式为 `position fen <FEN> moves <MOVES>`
        * `time`: 限定搜索时间，单位为毫秒
        * `depth`: 限定搜索深度
        """
        self.send_line(position)
        self.send_line(f"go time {time} depth {depth}")
        lines = await self.read_lines("bestmove")
        if not lines:
            raise EngineError("引擎无法获取合适的着法")
        match = re.search(r"bestmove ([a-zA-Z]\d[a-zA-Z]\d)", lines[-1])
        if not match:
            raise EngineError("引擎返回的结果形式不正确")
        return Move.from_ucci(match.group(1))
