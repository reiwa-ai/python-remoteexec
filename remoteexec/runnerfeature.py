from typing import List, Dict, Tuple, Union, Callable, Optional, Callable
from enum import Enum
from collections import namedtuple
import warnings
import threading
import time
import copy
import ast

from .exceptions import *
from .hooks import *


class RunningFeatureBase:
    """RunningFeatureBase
    SnippetRunnerの実行時に利用するFeatureを定義するBaseクラス
    
    """
    def __init__(self):
        self.rank = 999

    def update_tree(self,
                    root:ast.AST,
                    ext_objects:Optional[Dict[str,object]]):
        return



class RunningWithoutImport(RunningFeatureBase):
    """RunningWithoutImport
    import文を除去する
    """
    def __init__(self):
        super().__init__()
        self.rank = 0

    def update_tree(self,
                    root:ast.AST,
                    ext_objects:Optional[Dict[str,object]]):
        for leaf in ast.walk(root):
            try:
                body = leaf.body
            except AttributeError:
                body = None
            if body is not None and type(body) is list:
                for index in range(len(body)-1, -1, -1):
                    if type(body[index]) is ast.Import or type(body[index]) is ast.ImportFrom:
                        del body[index]
        for leaf in ast.walk(root):
            if type(leaf) is ast.Import or type(leaf) is ast.ImportFrom:
                raise SnippetProhibitionError


class RunningWithSteppingCheck(RunningFeatureBase):
    """RunningWithSteppingCheck

    Pythonコードを1ステップ毎に実行しHookを実行する
    error_hook_classのHookの戻り値でエラーの時の実行方針を設定できる

    Args:
        prefix_hook_class (StepHook): 1ステップ実行前のHook
        postfix_hook_class (StepHook): 1ステップ実行後のHook
        error_hook_class (StepErrorHook): エラー時のHook

    Examples:

        >>> hook_return_code = StepErrorApproach.DEFAULT
        >>> class MyPrefixHook(StepHook):
        >>>     def hook(self, id:int, lineno:int):
        >>>         print(f"MyPrefixHook - {lineno}")
        >>> class MyPostfixHook(StepHook):
        >>>     def hook(self, id:int, lineno:int):
        >>>         print(f"MyPostfixHook - {lineno}")
        >>> feature = RunningWithSteppingCheck(prefix_hook_class=MyPrefixHook, postfix_hook_class=MyPostfixHook)
        >>> code = '''print('A')
        >>> print('B')
        >>> print('C')
        >>> '''
        >>> runner = SnippetRunnerLocal()
        >>> hook_return_code = StepErrorApproach.IGNORE_AND_CONTINUE
        >>> runner.exec(code, cond=RunningConditions(), features=[feature])
        MyPrefixHook - 1
        A
        MyPostfixHook - 1
        MyPrefixHook - 2
        B
        MyPostfixHook - 2
        MyPrefixHook - 3
        C
        MyPostfixHook - 3

    Note:
        エラーハンドリングに例外処理を使うので、実行コードが例外のraise/catchを行う場合、
        StepErrorApproach.DEFAULT以外を返すと、コードの動作が変わる可能性がある
    """
    def __init__(self, 
                 prefix_hook_class:object=StepHook,
                 postfix_hook_class:object=StepHook,
                 error_hook_class:object=StepErrorHook):
        super().__init__()
        self.rank = 1
        self.prefix_hook_class = prefix_hook_class
        self.postfix_hook_class = postfix_hook_class
        self.error_hook_class = error_hook_class

    def update_tree(self,
                    root:ast.AST,
                    ext_objects:Optional[Dict[str,object]]):
        hooktargets = []

        for leaf in ast.walk(root):
            try:
                body = leaf.body
            except AttributeError:
                body = None
            if body is not None and type(body) is list:
                for index in range(len(body)):
                    try:
                        lineno = body[index].lineno
                    except AttributeError:
                        lineno = 0
                    try_prefix = compile(f'__step_prefix_hook__({id(body[index])},{lineno})', '', 'exec', ast.PyCF_ONLY_AST).body[0]
                    try_postfix = compile(f'__step_postfix_hook__({id(body[index])},{lineno})', '', 'exec', ast.PyCF_ONLY_AST).body[0]
                    try_exter = compile(f'try:\n  0\nexcept Exception as __e:\n  __step_error_hook__({id(body[index])},{lineno},__e)', '', 'exec', ast.PyCF_ONLY_AST).body[0]
                    try_exter.body = [try_prefix,body[index],try_postfix]
                    body[index] = try_exter
                    hooktargets.append(HookTarget(id(body[index])))
                try_inter = compile(f'try:\n  0\nexcept SnippetStepBreak:\n  pass', '', 'exec', ast.PyCF_ONLY_AST).body[0]
                try_inter.body = body
                leaf.body = [try_inter]

        prefix_hook, postfix_hook, error_hook = None, None, None
        if self.prefix_hook_class is not None:
            prefix_hook = self.prefix_hook_class(hooktargets)
        if self.postfix_hook_class is not None:
            postfix_hook = self.postfix_hook_class(hooktargets)
        if self.error_hook_class is not None:
            error_hook = self.error_hook_class(hooktargets)

        def __step_prefix_hook__(id:int, lineno:int):
            if prefix_hook is not None and isinstance(prefix_hook, StepHook):
                prefix_hook.hook(id=id, lineno=lineno)
        def __step_postfix_hook__(id:int, lineno:int):
            if postfix_hook is not None and isinstance(postfix_hook, StepHook):
                postfix_hook.hook(id=id, lineno=lineno)
        def __step_error_hook__(id:int, lineno:int, e:Exception):
            if isinstance(e, SnippetException) and not isinstance(e, SnippetError):
                raise e
            if error_hook is not None and isinstance(error_hook, StepErrorHook):
                result = error_hook.hook(id=id, lineno=lineno)
                if result == StepErrorApproach.DEFAULT:
                    raise e
                elif result == StepErrorApproach.RAISE_ERROR:
                    raise SnippetStepError(e)
                elif result == StepErrorApproach.IGNORE_AND_BREAK:
                    raise SnippetStepBreak(e)

        assert "__step_prefix_hook__" not in ext_objects
        ext_objects["__step_prefix_hook__"] = __step_prefix_hook__
        assert "__step_postfix_hook__" not in ext_objects
        ext_objects["__step_postfix_hook__"] = __step_postfix_hook__
        assert "__step_error_hook__" not in ext_objects
        ext_objects["__step_error_hook__"] = __step_error_hook__
        ext_objects["SnippetStepBreak"] = SnippetStepBreak
        ext_objects["Exception"] = Exception


class RunningWithIgnoreError(RunningWithSteppingCheck):
    """RunningWithIgnoreError

    Pythonコードを1ステップ毎に実行しエラーをチェックする
    error_approachでエラーの時の実行方針を設定できる
    StepErrorApproach.DEFAULT: 通常通りの例外を送出
    StepErrorApproach.RAISE_ERROR: SnippetStepError例外を送出
    StepErrorApproach.IGNORE_AND_CONTINUE: 無視してその場から強引に実行を継続
    StepErrorApproach.IGNORE_AND_BREAK: コードブロックの終わりに移動して実行を継続

    Args:
        error_approach (StepErrorApproach): エラー発生時の対処法

    Examples:

        >>> feature = RunningWithIgnoreError(StepErrorApproach.IGNORE_AND_CONTINUE)
        >>> code = '''for i in range(3):
        >>>     print('start')
        >>>     print(100 / 0)  # raise error
        >>>     print('end')
        >>> '''
        >>> runner = SnippetRunnerLocal()
        >>> runner.exec(code, cond=RunningConditions(), features=[feature])
        start
        end
        start
        end
        start
        end
        >>> feature = RunningWithIgnoreError(StepErrorApproach.IGNORE_AND_BREAK)
        >>> runner.exec(code, cond=RunningConditions(), features=[feature])
        start
        start
        start

    Note:
        エラーハンドリングに例外処理を使うので、実行コードが例外のraise/catchを行う場合、
        StepErrorApproach.DEFAULT以外を渡すと、コードの動作が変わる可能性がある
    """
    def __init__(self, 
                 error_approach:StepErrorApproach=StepErrorApproach.DEFAULT):
        class _StepErrorHook(StepErrorHook):
            def hook(self, id:int, lineno:int) -> StepErrorApproach:
                return error_approach
        super().__init__(error_hook_class=_StepErrorHook)


class RunningWithEvalCheck(RunningFeatureBase):
    """RunningWithEvalCheck

    Pythonコードの1ステップ毎に変数をチェックするデバッグ用Feature
    target_hook_classのHookの戻り値でチェックする変数を指定できる
    チェックする変数はその後に呼び出されるeval_hook_classに渡される

    Args:
        target_hook_class (StepHook): 1ステップ実行前のHook
        eval_hook_class (StepHook): 1ステップ実行後のHook

    Examples:

        >>> class MyStepTargetHook(StepTargetHook):
        >>>     def hook(self, id:int, lineno:int) -> Optional[List[str]]:
        >>>         return ["target"] if lineno==2 or lineno==4 else None
        >>> class MyStepEvalHook(StepEvalHook):
        >>>     def hook(self, id:int, lineno:int, name:str, value:Optional[object]):
        >>>         print(f"StepEvalHook -- lineno={lineno} name={name} value={value}")
        >>> feature = RunningWithEvalCheck(target_hook_class=MyStepTargetHook,
        >>>                            eval_hook_class=MyStepEvalHook)
        >>> code = '''target = "abcde"
        >>> print('start')
        >>> print(target:='fghij')
        >>> print('end')
        >>> '''
        >>> runner = SnippetRunnerLocal()
        >>> hook_return_code = StepErrorApproach.IGNORE_AND_CONTINUE
        >>> runner.exec(code, cond=RunningConditions(), features=[feature])
        start
        StepEvalHook -- lineno=2 name=target value=abcde
        fghij
        end
        StepEvalHook -- lineno=4 name=target value=fghij

    Note:
        変数チェックにevalを使用するので、allow_global_functionsにevalを追加する必要がある
        その事によりセキュリティリスクが発生するので、このFeatureはデバッグのためにのみ使う事
    """
    def __init__(self, 
                 target_hook_class:object=StepTargetHook,
                 eval_hook_class:object=StepEvalHook):
        super().__init__()
        self.rank = 2
        self.target_hook_class = target_hook_class
        self.eval_hook_class = eval_hook_class

    def update_tree(self,
                    root:ast.AST,
                    ext_objects:Optional[Dict[str,object]]):
        hooktargets = []

        for leaf in ast.walk(root):
            try:
                body = leaf.body
            except AttributeError:
                body = None
            if body is not None and type(body) is list:
                newbody = []
                for index in range(len(body)):
                    try:
                        lineno = body[index].lineno
                    except AttributeError:
                        lineno = 0
                    eval_check = compile(f'for __n in __step_target_hook__({id(body[index])},{lineno}):\n  __step_eval_hook__({id(body[index])},{lineno},__n,eval(__n))', '', 'exec', ast.PyCF_ONLY_AST).body[0]
                    newbody.append(body[index])
                    newbody.append(eval_check)
                    hooktargets.append(HookTarget(id(body[index])))
                leaf.body = newbody

        target_hook, eval_hook = None, None
        if self.target_hook_class is not None:
            target_hook = self.target_hook_class(hooktargets)
        if self.eval_hook_class is not None:
            eval_hook = self.eval_hook_class(hooktargets)

        def __step_target_hook__(id:int, lineno:int):
            if target_hook is not None and isinstance(target_hook, StepTargetHook):
                evalnames = target_hook.hook(id=id, lineno=lineno)
                if evalnames is not None and type(evalnames) is list:
                    for name in evalnames:
                        if type(name) is not str:
                            return []
                    return evalnames
            return []

        def __step_eval_hook__(id:int, lineno:int, name:str, value:object):
            if eval_hook is not None and isinstance(eval_hook, StepEvalHook):
                eval_hook.hook(id=id, lineno=lineno, name=name, value=value)
                
        assert "__step_target_hook__" not in ext_objects
        ext_objects["__step_target_hook__"] = __step_target_hook__
        assert "__step_eval_hook__" not in ext_objects
        ext_objects["__step_eval_hook__"] = __step_eval_hook__


class RunningWithLoopHook(RunningFeatureBase):
    """RunningWithLoopHook

    ループの実行にHookを入れるFeature

    Args:
        hook_classes (List[LoopHook]): list of LoopHook
        includes_comp_loop (bool): 内包表記([_ for...]など)をループに数える
        forced_execution_mode (bool): ループを強制執行モードで実行

    Examples:

        hook_classesにLoopHookクラスを指定するとループ時にHookする

        >>> class MyCounterLoopHook(CounterLoopHook):
        >>>    def __init__(self, loops:List[HookTarget]):
        >>>        super().__init__(loops=loops, maxcount=5)
        >>> feature = RunningWithLoopHook([MyCounterLoopHook], forced_execution_mode=True)
        >>> code = '''for i in range(500):
        >>>     print('hoge')
        >>> '''
        >>> runner = SnippetRunnerLocal()
        >>> runner.exec(code, cond=RunningConditions(), features=[feature])
        >>> print("end")
        hoge
        hoge
        hoge
        hoge
        hoge
        end

    Note:
        forced_execution_modeがTrueのとき、FOR、WHILEなら強引に処理を続ける
    """
    def __init__(self,
                 hook_classes:List[object]=[LoopHook],
                 includes_comp_loop:bool=True,
                 forced_execution_mode:bool=False):
        super().__init__()
        self.rank = 5
        self.hook_classes = hook_classes
        self.includes_comp_loop = includes_comp_loop
        self.forced_execution_mode = forced_execution_mode

    def _get_tree(self, root:ast.AST) -> List[object]:        
        LoopHookTarget = namedtuple('LoopHookTarget', ['id', 'depth', 'loop', 'children'])

        def update_loop_node(node):
            if self.forced_execution_mode:
                loop_exter = compile(f'try:\n  0\nexcept SnippetOvertime:\n  break', '', 'exec', ast.PyCF_ONLY_AST).body[0]
                loop_exter.body = node.body
                node.body = [loop_exter]
                
        def find_loop_children(tree, depth, hooks):
            newhooks = None
            for node in ast.iter_child_nodes(tree):
                if type(node) is ast.While: # while文なら
                    loop_inter = compile(f'__loop_inter_hook__(id={id(node)})', '', 'exec', ast.PyCF_ONLY_AST).body[0]
                    node.body.insert(0, loop_inter)
                    update_loop_node(node)
                    newhooks = []
                    hooks.append(LoopHookTarget(id(node), depth, LoopHookType.WHILE, newhooks))
                elif type(node) is ast.AsyncFor or type(node) is ast.For: # for文なら
                    loop_inter = compile(f'__loop_inter_hook__(id={id(node)})', '', 'exec', ast.PyCF_ONLY_AST).body[0]
                    node.body.insert(0, loop_inter)
                    update_loop_node(node)
                    newhooks = []
                    hooks.append(LoopHookTarget(id(node), depth, LoopHookType.FOR, newhooks))
                elif type(node) is ast.ListComp or type(node) is ast.SetComp or type(node) is ast.GeneratorExp or type(node) is ast.DictComp: # [_ for ...]文なら
                    if self.includes_comp_loop:
                        elt = node.value if type(node) is ast.DictComp else node.elt
                        loop_inter = compile(f'__loop_inter_hook__(id={id(node)},obj=obj)', '', 'exec', ast.PyCF_ONLY_AST).body[0]
                        for kw in loop_inter.value.keywords:
                            if str(kw.arg) == 'obj':
                                kw.value = elt
                        if type(node) is ast.DictComp:
                            node.value = loop_inter.value
                        else:
                            node.elt = loop_inter.value
                        newhooks = []
                        hooks.append(LoopHookTarget(id(node), depth, LoopHookType.COMP, []))
                if newhooks is None:
                    find_loop_children(node, depth, hooks)
                else:
                    find_loop_children(node, depth+1, newhooks)
                
        hook_nodes = []
        find_loop_children(root, 0, hook_nodes)

        return hook_nodes

    def update_tree(self,
                    root:ast.AST,
                    ext_objects:Optional[Dict[str,object]]):
        hook_nodes = self._get_tree(root)
        all_hook_targets = []
        id_hook_nodes = {}
        def add_hook_node(nodes):
            nonlocal all_hook_targets, id_hook_nodes
            for node in nodes:
                all_hook_targets.append(HookTarget(node.id))
                id_hook_nodes[node.id] = node
                if node.children is not None:
                    add_hook_node(node.children)
        add_hook_node(hook_nodes)

        hooks = [clz(all_hook_targets) for clz in self.hook_classes]

        def clear_hook_node(nodes):
            for node in nodes:
                for hook in hooks:
                    if isinstance(hook, LoopHook):
                        hook.clear_loop(id=node.id)                
                if node.children is not None:
                    clear_hook_node(node.children)

        def __loop_inter_hook__(id:int, obj:Optional[object]=None):
            try:
                lineno = id_hook_nodes[id].lineno
            except AttributeError:
                lineno = 0
            if id_hook_nodes[id].children is not None:
                clear_hook_node(id_hook_nodes[id].children)
            for hook in hooks:
                if hook is not None and isinstance(hook, HookBase):
                    hook.hook(id=id, lineno=lineno)
            return obj

        assert "__loop_inter_hook__" not in ext_objects
        ext_objects["__loop_inter_hook__"] = __loop_inter_hook__
        ext_objects["SnippetOvertime"] = SnippetOvertime


class RunningWithOuterFrequency(RunningWithLoopHook):
    """RunningWithOuterFrequency

    最も外側のループの実行周波数を指定してコードを実行するFeature
    外側のループはFORとWHILEのみで、複数あるときは全てに周波数を適用
    ループ内ループの場合に、内側ループのタイムアウト処理を指定できる

    Args:
        frequency (float): 最も外側のループの最小実行周波数
        throttling_mode (bool): 周波数に合わせるスロットリングを行うか
        max_loop_timeout (float): 内側ループの最大実行時間
        max_outer_loop_count (int): 外側ループの最大実行回数
        max_inner_loop_count (int): 内側ループの最大実行回数
        includes_comp_loop (bool): 内包表記([_ for...]など)をループに数える
        forced_execution_mode (bool): ループを例外発生時に無視して強制実行

    Examples:

        frequencyを指定して実行するとその周波数で実行される

        >>> feature = RunningWithOuterFrequency(frequency=50)
        >>> code = '''for i in range(500):
        >>>     if i%100==0:
        >>>         print('hoge')
        >>> '''
        >>> runner = SnippetRunnerLocal()
        >>> start_time = time.time()
        >>> runner.exec(code, cond=RunningConditions(), features=[feature])
        hoge
        hoge
        hoge
        hoge
        hoge
        >>> print(round(time.time() - start_time))
        10

    Note:
        frequency<=0なら周波数制御は行わない(スロットリング最大)
        frequencyとthrottling_modeのどちらかは指定する必要がある
        max_outer_loop_count、max_inner_loop_count<0は無限ループを許可
        forced_execution_modeがTrueのとき、FOR、WHILEなら、実行回数オーバー、
        タイムアウト時に例外を送出せず、ループを強制中断して強引に処理を続ける
    """
    def __init__(self,
                 frequency:float=-1.,
                 throttling_mode:bool=True,
                 max_loop_timeout:float=0.9,
                 max_outer_loop_count:int=-1,
                 max_inner_loop_count:int=-1,
                 includes_comp_loop:bool=True,
                 forced_execution_mode:bool=False):
        super().__init__(includes_comp_loop=includes_comp_loop, forced_execution_mode=forced_execution_mode)
        assert not(frequency<=0 and throttling_mode==True), "frequency<=0 and throttling mode cannot be used at the same time"
        self.frequency = frequency
        self.throttling_mode = throttling_mode
        self.max_loop_timeout = max_loop_timeout
        self.max_outer_loop_count = max_outer_loop_count
        self.max_inner_loop_count = max_inner_loop_count
        self.extra_hooks = []
    
    def update_tree(self,
                    root:ast.AST,
                    ext_objects:Optional[Dict[str,object]]):
        hook_nodes = self._get_tree(root)
        all_hook_targets = []
        id_hook_nodes = {}
        def add_hook_node(nodes):
            nonlocal all_hook_targets, id_hook_nodes
            for node in nodes:
                all_hook_targets.append(HookTarget(node.id))
                id_hook_nodes[node.id] = node
                if node.children is not None:
                    add_hook_node(node.children)
        add_hook_node(hook_nodes)

        hooks = []

        frequency_hook_targets = []
        outer_hook_targets = []
        inner_hook_targets = []
        for target in id_hook_nodes.values():
            if target.depth > 0:
                inner_hook_targets.append(HookTarget(target.id))
            elif target.depth == 0:
                outer_hook_targets.append(HookTarget(target.id))
            if target.depth == 0 and ( \
                    target.loop == LoopHookType.FOR or \
                    target.loop == LoopHookType.WHILE):
                frequency_hook_targets.append(HookTarget(target.id))

        if self.throttling_mode:
            hooks.append(FrequencyLoopHook(frequency_hook_targets, self.frequency))

        if self.max_loop_timeout > 0:
            hooks.append(TimeoutLoopHook(inner_hook_targets, self.max_loop_timeout))

        if self.max_outer_loop_count >= 0:
            hooks.append(CounterLoopHook(outer_hook_targets, self.max_outer_loop_count))

        if self.max_inner_loop_count >= 0:
            hooks.append(CounterLoopHook(inner_hook_targets, self.max_inner_loop_count))

        def clear_hook_node(nodes):
            for node in nodes:
                for hook in hooks + self.extra_hooks:
                    if isinstance(hook, LoopHook):
                        hook.clear_loop(id=node.id)                
                if node.children is not None:
                    clear_hook_node(node.children)

        def __loop_inter_hook__(id:int, obj:Optional[object]=None):
            try:
                lineno = id_hook_nodes[id].lineno
            except AttributeError:
                lineno = 0
            if id_hook_nodes[id].children is not None:
                clear_hook_node(id_hook_nodes[id].children)
            for hook in hooks + self.extra_hooks:
                if hook is not None and isinstance(hook, HookBase):
                    hook.hook(id=id, lineno=lineno)
            return obj

        assert "__loop_inter_hook__" not in ext_objects
        ext_objects["__loop_inter_hook__"] = __loop_inter_hook__
        ext_objects["SnippetOvertime"] = SnippetOvertime

