from enum import Enum
from typing import List
import time

from ..exceptions import *
from .hookbase import HookTarget, HookBase

class LoopHookType(Enum):
    """LoopHookType
    ループの種類
    """
    WHILE = 1
    FOR = 2
    COMP = 3


class LoopHook(HookBase):
    """LoopHook
    ループ実行に対するフック関数の基底クラス
    """
    def __init__(self, loops:List[HookTarget]):
        super().__init__(targets=loops)
    
    def clear_loop(self, id:int):
        pass


class CounterLoopHook(LoopHook):
    """CounterLoopHook
    ループ実行回数でループを制御するフック関数
    """
    def __init__(self, loops:List[HookTarget], maxcount:int):
        super().__init__(loops=loops)
        self.counter = {l.id:0 for l in loops}
        self.maxcount = maxcount

    def hook(self, id:int, lineno:int):
        def _hook():
            self.counter[id] += 1
            if self.counter[id] > self.maxcount:
                raise SnippetLoopOvertime()
        return _hook() if id in self.counter else super().hook(id=id, lineno=lineno)
    
    def clear_loop(self, id:int):
        if id in self.counter:
            self.counter[id] = 0


class TimeoutLoopHook(LoopHook):
    """TimeoutLoopHook
    ループ実行タイムアウトでループを制御するフック関数
    """
    def __init__(self, loops:List[HookTarget], timeout:float):
        super().__init__(loops=loops)
        self.timeout = timeout
        self.last_time = {l.id:0 for l in loops}

    def hook(self, id:int, lineno:int):
        def _hook():
            if id in self.last_time:
                if self.last_time[id] > 0 and self.last_time[id] + self.timeout < time.time():
                    raise SnippetLoopTimeout
                self.last_time[id] = time.time()
        return _hook() if id in self.last_time else super().hook(id=id, lineno=lineno)

    def clear_loop(self, id:int):
        if id in self.last_time:
            self.last_time[id] = 0


class FrequencyLoopHook(LoopHook):
    """FrequencyLoopHook
    ループ実行周波数でループを制御するフック関数
    """
    def __init__(self, loops:List[HookTarget], frequency:float=0.0):
        super().__init__(loops=loops)
        self.counter = {l.id:0 for l in loops}
        self.avgruntime = {l.id:[0,0] for l in loops}
        self.befruntime = {l.id:0 for l in loops}
        self.unittime = 1.0 / frequency
        self.all_loops = loops

    def hook(self, id:int, lineno:int):
        def _hook():
            if self.befruntime[id] > 0:
                delta = time.time() - self.befruntime[id]
                if delta < 0:
                    raise SnippetLoopTimeout()
                self.avgruntime[id][0] = self.avgruntime[id][0] * 0.99 + delta
                self.avgruntime[id][1] = self.avgruntime[id][1] * 0.99 + 1.0
                average = self.avgruntime[id][0] / self.avgruntime[id][1]
                if self.counter[id] > 100:
                    sleeptime = self.unittime - average
                else:
                    sleeptime = self.unittime - delta
                if sleeptime > 0:
                    time.sleep(sleeptime)
            self.counter[id] += 1
            self.befruntime[id] = time.time()
        return _hook() if id in self.avgruntime else super().hook(id=id, lineno=lineno)
    
    def clear_loop(self, id:int):
        if id in self.counter:
            self.counter[id] = 0
        if id in self.avgruntime:
            self.avgruntime[id][0] = 0
            self.avgruntime[id][1] = 0
        if id in self.befruntime:
            self.befruntime[id] = 0
