from enum import Enum
from typing import List, Callable, Optional
import time

from ..exceptions import *
from .hookbase import HookTarget, HookBase

class StepErrorApproach(Enum):
    """StepErrorApproach
    例外発生時の挙動
    """
    DEFAULT = 1
    RAISE_ERROR = 2
    IGNORE_AND_CONTINUE = 3
    IGNORE_AND_BREAK = 4


class StepHook(HookBase):
    """StepHook
    一行毎の実行フック関数の基底クラス
    """
    def __init__(self, targets:List[HookTarget]):
        super().__init__(targets=targets)

    def hook(self, id:int, lineno:int):
        pass


class StepErrorHook(HookBase):
    """StepErrorHook
    一行毎の実行で例外発生時のフック関数の基底クラス
    """
    def __init__(self, targets:List[HookTarget]):
        super().__init__(targets=targets)

    def hook(self, id:int, lineno:int) -> StepErrorApproach:
        return StepErrorApproach.DEFAULT


class StepTargetHook(StepHook):
    """StepTargetHook
    一行毎の実行のフック関数の基底クラス
    """
    def __init__(self, targets:List[HookTarget]):
        super().__init__(targets=targets)

    def hook(self, id:int, lineno:int) -> Optional[List[str]]:
        None


class StepEvalHook(StepHook):
    """StepEvalHook
    一行毎の実行の実行結果取得フック関数の基底クラス
    """
    def __init__(self, targets:List[HookTarget]):
        super().__init__(targets=targets)

    def hook(self, id:int, lineno:int, name:str, value:Optional[object]):
        pass

