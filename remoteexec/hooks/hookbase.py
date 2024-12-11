from typing import List

from ..exceptions import *

class HookTarget:
    """HookTarget
    フック関数を定義するターゲットのコード
    """
    def __init__(self, id:int):
        self.id = id


class HookBase:
    """HookBase
    実行コードに対して定義されるフック関数
    """
    def __init__(self, targets:List[HookTarget]):
        pass
    
    def hook(self, id:int, lineno:int):
        pass