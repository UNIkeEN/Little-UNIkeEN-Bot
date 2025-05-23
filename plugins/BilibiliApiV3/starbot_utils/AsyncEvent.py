"""
发布-订阅模式异步事件类支持
"""

import asyncio
from typing import Any, Coroutine, Dict, Optional


class AsyncEvent:
    """
    发布-订阅模式异步事件类支持

    特殊事件：__ALL__ 所有事件均触发
    """

    __handlers: Optional[Dict] = {}
    __running_tasks = set()

    def __init__(self):
        self.__handlers = {}

    def add_event_listener(self, name: str, handler: Coroutine):
        """
        注册事件监听器

        Args:
            name: 事件名
            handler: 回调异步函数
        """
        name = name.upper()
        if name not in self.__handlers:
            self.__handlers[name] = []
        self.__handlers[name].append(handler)

    def on(self, event_name: str):
        """
        装饰器注册事件监听器

        Args:
            event_name: 事件名
        """

        def decorator(func: Coroutine):
            self.add_event_listener(event_name, func)
            return func

        return decorator

    def remove_event_listener(self, name: str, handler: Coroutine) -> bool:
        """
        移除事件监听函数

        Args:
            name: 事件名
            handler: 要移除的函数

        Returns:
            是否移除成功
        """
        name = name.upper()
        if name in self.__handlers:
            if handler in self.__handlers[name]:
                self.__handlers[name].remove(handler)
                return True
        return False

    def dispatch(self, name: str, data: Any = None):
        """
        异步发布事件

        Args:
            name: 事件名
            data: 事件附加数据。默认：None
        """
        name = name.upper()
        if name in self.__handlers:
            for coroutine in self.__handlers[name]:
                task = asyncio.create_task(coroutine(data))
                self.__running_tasks.add(task)
                task.add_done_callback(lambda t: self.__running_tasks.remove(t))

        if name != '__ALL__':
            self.dispatch('__ALL__', {
                "name": name,
                "data": data
            })
