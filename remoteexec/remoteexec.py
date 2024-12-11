from typing import List, Dict, Tuple, Union, Callable, Optional, Callable
from enum import Enum
from collections import namedtuple
from logging import getLogger
from subprocess import PIPE, Popen
import warnings
import socket
import signal
import threading
import ctypes
import time
import copy
import ast

from .exceptions import *
from .hooks import *
from .runnerfeature import *
from .communicate import *

COMMON_BUILTINS = ['abs','all','any','bin','bool','bytearray','bytes','callable',
                   'chr','classmethod','complex','delattr','dict','divmod','enumerate',
                   'filter','float','format','frozenset','getattr','hasattr','hash',
                   'hex','id','int','isinstance','issubclass','iter','len','list',
                   'map','max','min','next','object','oct','ord','pow','property',
                   'range','reversed','round','set','setattr','slice','sorted',
                   'staticmethod','str','sum','super','tuple','type','vars','zip']

COMMON_MODULES = ['string','re','difflib','textwrap','unicodedata','stringprep',
                  'datetime','calendar','collections','heapq','bisect','array','copy',
                  'enum','numbers','math','cmath','fractions','random','statistics',
                  'itertools','operator','hashlib','time','json','base64']

class RunningConditions:
    """RunningConditions

    コードの動的実行を行う実行条件を定義するクラス

    Args:
        shared_objects (Dict[str,object]): コード内変数と共有オブジェクト
        total_timeout_sec (float): 実行タイムアウト(0以下でタイムアウト無し)
        dynamic_import (bool): コード内import文を許可する
        allow_global_functions (str): 利用を許可するPythonビルトイン関数
        allow_import_modules (str): 予めインポートするPythonパッケージ
        force_globals (object): globalsを強制的に上書きする(非推奨)
        force_locals (object): localsを強制的に上書きする(非推奨)

    Note:
        snippetchecker.support.make_cleaned_builtinsを参照
    """

    def __init__(self,
                 shared_objects:Optional[Dict[str,object]]=None,
                 total_timeout_sec:float=0,
                 dynamic_import:bool=False,
                 allow_global_functions:Optional[List[str]]=COMMON_BUILTINS,
                 allow_import_modules:Optional[List[str]]=COMMON_MODULES,
                 force_globals:Optional[object]=None,
                 force_locals:Optional[object]=None):
        self.shared_objects = shared_objects if shared_objects is not None else dict()
        self.total_timeout_sec = total_timeout_sec
        self.dynamic_import = dynamic_import
        self.allow_global_functions = allow_global_functions
        self.allow_import_modules = allow_import_modules
        self.force_globals = force_globals
        self.force_locals = force_locals

class SnippetStepHook:
    def hook(self, id:int, lineno:int):
        pass
class SnippetStepErrorHook:
    def hook(self, id:int, lineno:int)->StepErrorApproach:
        pass
class SnippetLoopHook:
    def hook(self, id:int, lineno:int):
        pass
    def clear_loop(self, id:int):
        pass

class SnippetRunner:
    def __init__(self,
                 local_run:bool=False,
                 docker_run:bool=False,
                 docker_command:Optional[List[str]]=None,
                 tcp_run:bool=False,
                 tcp_hostname:str=None,
                 tcp_port:int=9165,
                 sync_frequency:float = -1,
                 sync_conflict_policy:ConflictSolvePolicy = ConflictSolvePolicy.HOST_PRIORITIZED,
                 sync_snippet_share_only:bool = True,
                 sync_shared_depth:int = -1):
        assert sum([local_run,docker_run,tcp_run])==1, 'local_run,docker_run,tcp_run must only one True'
        self.local_run = local_run
        self.docker_run = docker_run
        self.docker_command = docker_command
        self.tcp_run = tcp_run
        self.tcp_hostname = tcp_hostname
        self.tcp_port = tcp_port
        self.sync_frequency = sync_frequency
        self.sync_conflict_policy = sync_conflict_policy
        self.sync_snippet_share_only = sync_snippet_share_only
        self.sync_shared_depth = sync_shared_depth
    """SnippetRunner

    コードの動的実行を行うクラス

    Args:
        local_run (bool): ローカル実行
        docker_run (bool): コンテナ内実行
        docker_command (str): コンテナ起動コマンド
        tcp_run (bool): リモート実行
        tcp_hostname (str): ホスト名
        tcp_port (int): ポート番号
        sync_frequency (float): 同期周波数
        sync_conflict_policy (ConflictSolvePolicy): 同期ポリシー
        sync_snippet_share_only (bool): @snippet_shareのみ同期
        sync_shared_depth (bool): 同期オブジェクトの再帰深さ
    """

    def exec(self,
             code:str,
             cond:RunningConditions,
             frequency:float=-1.,
             throttling_mode:bool=True,
             max_loop_timeout:float=0.9,
             max_outer_loop_count:int=-1,
             max_inner_loop_count:int=-1,
             includes_comp_loop:bool=True,
             forced_execution_mode:bool=False,
             loop_hook:Optional[SnippetLoopHook]=None,
             step_prefix_hook:Optional[SnippetStepHook]=None,
             step_postfix_hook:Optional[SnippetStepHook]=None,
             error_hook:Optional[SnippetStepErrorHook]=None):
        """
        指定されたコードを実行する

        Args:
            code (str): 実行コード
            cond (RunningConditions): 実行条件データ
            frequency (float): 最も外側のループの最小実行周波数
            throttling_mode (bool): 周波数に合わせるスロットリングを行うか
            max_loop_timeout (float): 内側ループの最大実行時間
            max_outer_loop_count (int): 外側ループの最大実行回数
            max_inner_loop_count (int): 内側ループの最大実行回数
            includes_comp_loop (bool): 内包表記([_ for...]など)をループに数える
            forced_execution_mode (bool): ループを例外発生時に無視して強制実行
            loop_hook (SnippetLoopHook): ループが実行される度に呼び出されるHook
            step_prefix_hook (SnippetStepHook): 1ステップ実行される度に呼び出されるHook
            step_postfix_hook (SnippetStepHook): 1ステップ実行される度に呼び出されるHook
            error_hook (SnippetStepErrorHook): 実行時Exceptionがraiseした時に呼び出されるHook

        Note:
            error_hookを指定した場合、エラーハンドリングに例外処理を使うので、
            実行コードが例外のraise/catchを行う場合、
            StepErrorApproach.DEFAULT以外を渡すと、コードの動作が変わる可能性がある
            error_hookの戻り値は以下のいずれか
            StepErrorApproach.DEFAULT: 通常通りの例外を送出
            StepErrorApproach.RAISE_ERROR: SnippetStepError例外を送出
            StepErrorApproach.IGNORE_AND_CONTINUE: 無視してその場から強引に実行を継続
            StepErrorApproach.IGNORE_AND_BREAK: コードブロックの終わりに移動して実行を継続
        """
        if self.local_run:
            running_features = []

            class MyLoopHook(LoopHook):
                def hook(self, id:int, lineno:int):
                    loop_hook.hook(id=id, lineno=lineno)
                def clear_loop(self, id:int):
                    loop_hook.clear_loop(id=id)

            if frequency > 0 or throttling_mode==False or max_outer_loop_count >= 0 or max_inner_loop_count >= 0:
                loophookfeature = RunningWithOuterFrequency(frequency=frequency,
                                                            throttling_mode=throttling_mode,
                                                            max_loop_timeout=max_loop_timeout,
                                                            max_outer_loop_count=max_outer_loop_count,
                                                            max_inner_loop_count=max_inner_loop_count,
                                                            includes_comp_loop=includes_comp_loop,
                                                            forced_execution_mode=forced_execution_mode)
                if loop_hook is not None:
                    loophookfeature.extra_hooks.append(MyLoopHook([loop_hook]))
                running_features.append(loophookfeature)
            elif loop_hook is not None:
                running_features.append(RunningWithLoopHook([MyLoopHook]))

            if step_prefix_hook is not None or\
            step_postfix_hook is not None or\
            error_hook is not None:
                class MyPrefixHook(StepHook):
                    def hook(self, id:int, lineno:int):
                        step_prefix_hook.hook(id=id, lineno=lineno)
                class MyPostfixHook(StepHook):
                    def hook(self, id:int, lineno:int):
                        step_postfix_hook.hook(id=id, lineno=lineno)
                class MyErrorHook(StepErrorHook):
                    def hook(self, id:int, lineno:int) -> StepErrorApproach:
                        return StepErrorApproach(error_hook.hook(id=id, lineno=lineno))
                running_features.append(RunningWithSteppingCheck(prefix_hook_class=MyPrefixHook if step_prefix_hook is not None else None,
                                                                postfix_hook_class=MyPostfixHook if step_postfix_hook is not None else None,
                                                                error_hook_class=MyErrorHook if error_hook is not None else None))

            runner = SnippetRunnerLocal()
            runner.exec(code,
                        cond=cond,
                        features=running_features)
        elif self.docker_run:
            run_docker_command = copy.copy(self.docker_command)
            if '--sync_frequency' not in run_docker_command:
                run_docker_command.extend(['--sync_frequency', f'{self.sync_frequency}'])
            else:
                fq_idx = run_docker_command.index['--sync_frequency'] + 1
                if fq_idx < len(run_docker_command):
                    run_docker_command[fq_idx] = f'{self.sync_frequency}'
                else:
                    run_docker_command.append(f'{self.sync_frequency}')
                 
            class DockerCommunicationIO:
                def __init__(self):
                    self.task = Popen((run_docker_command), stdin=PIPE, stdout=PIPE, stderr=PIPE)
                
                def send(self, data:bytearray)->int:
                    n = self.task.stdin.write(data)
                    self.task.stdin.flush()
                    return n

                def recv(self, delimiter:bytes=b'\n')->bytearray:
                    r = self.task.stdout.readline()
                    if r == b'':
                        raise SnippetAbortException('docker running fail')
                    return r

                def close(self):
                    self.task.terminate()
                    self.task.wait()
            
            connection = DockerCommunicationIO()
            runner = SnippetRunnerRemote(connection=connection, sync_frequency=self.sync_frequency)
            runner.exec(code, cond)
        elif self.run_tcp:
            tcp_hostname, tcp_port = self.tcp_hostname, self.tcp_port
            class SocketCommunicationIO:
                def __init__(self):
                    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.socket.connect((tcp_hostname, tcp_port))
                    self.reader = self.socket.makefile('rw')

                def send(self, data:bytearray)->int:
                    n = self.reader.write(data.decode('UTF-8'))
                    self.reader.flush()

                def recv(self, delimiter:bytes=b'\n')->bytearray:
                    line = self.reader.readline()
                    return line.encode('UTF-8')

                def close(self):
                    self.reader.close()
                    self.socket.close()
            
            connection = SocketCommunicationIO()
            runner = SnippetRunnerRemote(connection=connection, sync_frequency=self.sync_frequency)
            runner.exec(code, cond)

    def run_local():
        return SnippetRunner(local_run=True)
    def run_docker(docker_command=['docker', 'run', '-i', 'snippetrunner:latest', 'python','-u', 'server.py'],
                   sync_frequency:float = 5,
                   sync_conflict_policy:ConflictSolvePolicy = ConflictSolvePolicy.HOST_PRIORITIZED,
                   sync_snippet_share_only:bool = True,
                   sync_shared_depth:int = -1):
        return SnippetRunner(docker_run=True,
                             docker_command=['docker', 'run', '-i', 'snippetrunner:latest', 'python','-u', 'server.py'],
                             sync_frequency=sync_frequency,
                             sync_conflict_policy=sync_conflict_policy,
                             sync_snippet_share_only=sync_snippet_share_only,
                             sync_shared_depth=sync_shared_depth)
    def run_tcp(tcp_hostname:str,
                tcp_port:int=9165,
                sync_frequency:float = 5,
                sync_conflict_policy:ConflictSolvePolicy = ConflictSolvePolicy.HOST_PRIORITIZED,
                sync_snippet_share_only:bool = True,
                sync_shared_depth:int = -1):
        return SnippetRunner(tcp_run=True,
                             tcp_hostname=tcp_hostname,
                             tcp_port=tcp_port,
                             sync_frequency=sync_frequency,
                             sync_conflict_policy=sync_conflict_policy,
                             sync_snippet_share_only=sync_snippet_share_only,
                             sync_shared_depth=sync_shared_depth)


class SnippetRunnerLocal:
    def __init__(self):
        super().__init__()
    """SnippetRunnerLocal
    コードの動的実行を行うクラス
    """

    def _exec(self,
             code:str,
             cond:RunningConditions,
             features:Optional[List[RunningFeatureBase]]=None):
        try:
            root = compile(code, '', 'exec', ast.PyCF_ONLY_AST)
        except SyntaxError as e:
            raise SnippetSyntaxError

        for leaf in ast.walk(root): # 禁則チェック
            if type(leaf) is ast.Name:
                if leaf.id.startswith('__'):
                    raise SnippetProhibitionError
        
        def make_cleaned_builtins(allow_global_functions:List[str],
                          allow_import_modules:List[str]) -> object:
            global_builtins = None
            if len(allow_global_functions) > 0:
                module_dict = __builtins__ if type(__builtins__) is dict else __builtins__.__dict__
                global_builtins = {name:module_dict.get(name, None) for name in allow_global_functions}
            if len(allow_import_modules) > 0:
                global_builtins = {} if global_builtins is None else global_builtins
                module_dict = __builtins__ if type(__builtins__) is dict else __builtins__.__dict__
                for modname in allow_import_modules:
                    global_builtins[modname] = __builtins__['__import__'](modname)
            if cond.dynamic_import:
                global_builtins['__import__'] = __builtins__['__import__']
            return global_builtins

        ext_objects = {}

        if not cond.dynamic_import:
            del_feature = RunningWithoutImport()
            del_feature.update_tree(root=root, ext_objects=ext_objects)

        if features is None or len(features)==0:
            features = []

        run_features = sorted(features, key=lambda x:(x.rank if isinstance(x, RunningFeatureBase) else -1))
        uniq_rank = set()
        for feature in run_features:
            assert feature.rank not in uniq_rank
            assert isinstance(feature, RunningFeatureBase) and feature.rank > 0
            feature.update_tree(root=root, ext_objects=ext_objects)
            uniq_rank.add(feature.rank)
        
        ext_objects['__builtins__'] = make_cleaned_builtins(allow_global_functions=cond.allow_global_functions,
                                        allow_import_modules=cond.allow_import_modules)
        for k,v in cond.shared_objects.items():
            ext_objects[k] = v
        ext_shared = {}

        if cond.force_globals:
            warnings.warn('force_globals is deprecated', DeprecationWarning)
            ext_objects = cond.force_globals
        if cond.force_locals:
            warnings.warn('force_locals is deprecated', DeprecationWarning)
            ext_shared = cond.force_locals

        self.running_feature = run_features
        exec(compile(root, '', 'exec'), ext_objects, ext_shared)

    def exec(self,
             code:str,
             cond:RunningConditions,
             features:Optional[List[RunningFeatureBase]]=None):
        """
        指定されたコードをローカル実行環境で実行する

        Args:
            code (str): 実行コード
            cond (RunningConditions): 実行条件データ
            features (List[RunningFeatureBase]): 利用するFeatures
        """
        timeout_sec = cond.total_timeout_sec
        if timeout_sec > 0:
            try:
                # run in the main thread of the main interpreter
                def timeout_hook(*args, **kwargs):
                    raise SnippetAbortException()
                original_func = signal.signal(signal.SIGALRM, timeout_hook)
                original_timer = signal.setitimer(signal.ITIMER_REAL, timeout_sec)
                start_time = time.time()
                result = None

                try:
                    result = self._exec(code, cond, features)
                    signal.signal(signal.SIGALRM, signal.SIG_DFL)
                except SnippetAbortException:
                    raise SnippetTotalTimeout()
                finally:
                    if original_func != signal.SIG_DFL and original_func != signal.SIG_IGN:
                        num_timer = original_timer[0]
                        if num_timer > 0:
                            num_timer = num_timer - (time.time() - start_time)
                        if num_timer < 0:
                            signal.signal(signal.SIGALRM, original_func)
                            signal.raise_signal(signal.SIGALRM)
                        else:
                            signal.setitimer(signal.ITIMER_REAL, num_timer)
                            signal.signal(signal.SIGALRM, original_func)
                return result
            except ValueError:
                # run in thread enabled
                the_thread_id = threading.current_thread().ident
                the_thread_stop = threading.Event()
                start_time = time.time()
                result = None
                def timeout_thread():
                    while True:
                        if the_thread_stop.is_set():
                            return
                        if start_time + timeout_sec < time.time():
                            break
                        time.sleep(0.01)
                    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(the_thread_id),
                                                        ctypes.py_object(SnippetAbortException))
                    if res == 0:
                        raise ValueError("thread state error")
                    elif res != 1:
                        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(the_thread_id), None)
                        raise SystemError("senf exception error")
                try:
                    watchthread = threading.Thread(target=timeout_thread)
                    watchthread.setDaemon(True)
                    watchthread.start()
                    result = self._exec(code, cond, features)
                except SnippetAbortException:
                    raise SnippetTotalTimeout()
                finally:
                    the_thread_stop.set()
                return result
        else:
            return self._exec(code, cond, features)


class SnippetRunnerRemote:
    def __init__(self,
                 connection:CommunicationIO,
                 sync_frequency:float = 5,
                 sync_conflict_policy:ConflictSolvePolicy = ConflictSolvePolicy.HOST_PRIORITIZED,
                 sync_snippet_share_only:bool = True,
                 sync_shared_depth:int = -1):
        super().__init__()
        self.connection = connection
        self.sync_frequency = sync_frequency
        self.sync_conflict_policy = sync_conflict_policy
        self.sync_snippet_share_only = sync_snippet_share_only
        self.sync_shared_depth = sync_shared_depth
        self.debug_mode = False
        self.logger = None
    """SnippetRunnerRemote

    コードの動的実行を行うクラス

    Args:
        connection (CommunicationIO): オブジェクト同期クラス
        sync_frequency (float): 同期周波数
        sync_conflict_policy (ConflictSolvePolicy): 同期ポリシー
        sync_snippet_share_only (bool): @snippet_shareのみ同期
        sync_shared_depth (bool): 同期オブジェクトの再帰深さ
    """

    def exec(self,
             code:str,
             cond:RunningConditions,
             frequency:float=-1.,
             throttling_mode:bool=True,
             max_loop_timeout:float=0.9,
             max_outer_loop_count:int=-1,
             max_inner_loop_count:int=-1,
             includes_comp_loop:bool=True,
             forced_execution_mode:bool=False,
             loop_hook:SnippetLoopHook=None,
             step_prefix_hook:SnippetStepHook=None,
             step_postfix_hook:SnippetStepHook=None,
             error_hook:SnippetStepErrorHook=None):
        """
        指定されたコードをリモート実行環境で実行する

        Args:
            code (str): 実行コード
            cond (RunningConditions): 実行条件データ
            frequency (float): 最も外側のループの最小実行周波数
            throttling_mode (bool): 周波数に合わせるスロットリングを行うか
            max_loop_timeout (float): 内側ループの最大実行時間
            max_outer_loop_count (int): 外側ループの最大実行回数
            max_inner_loop_count (int): 内側ループの最大実行回数
            includes_comp_loop (bool): 内包表記([_ for...]など)をループに数える
            forced_execution_mode (bool): ループを例外発生時に無視して強制実行
            loop_hook (SnippetLoopHook): ループが実行される度に呼び出されるHook
            step_prefix_hook (SnippetStepHook): 1ステップ実行される度に呼び出されるHook
            step_postfix_hook (SnippetStepHook): 1ステップ実行される度に呼び出されるHook
            error_hook (SnippetStepErrorHook): 実行時Exceptionがraiseした時に呼び出されるHook

        Note:
            error_hookを指定した場合、エラーハンドリングに例外処理を使うので、
            実行コードが例外のraise/catchを行う場合、
            StepErrorApproach.DEFAULT以外を渡すと、コードの動作が変わる可能性がある
            error_hookの戻り値は以下のいずれか
            StepErrorApproach.DEFAULT: 通常通りの例外を送出
            StepErrorApproach.RAISE_ERROR: SnippetStepError例外を送出
            StepErrorApproach.IGNORE_AND_CONTINUE: 無視してその場から強引に実行を継続
            StepErrorApproach.IGNORE_AND_BREAK: コードブロックの終わりに移動して実行を継続
        """
        assert cond.force_globals is None, 'force_globals is unsupported in remote run'
        assert cond.force_locals is None, 'force_locals is unsupported in remote run'

        class plain_loop_hook:
            def hook(self, id:int):
                loop_hook.hook(id)
            def clear_loop(self, id:int):
                loop_hook.clear_loop(id)

        class plain_step_prefix_hook:
            def hook(self, id:int):
                step_prefix_hook.hook(id)

        class plain_step_postfix_hook:
            def hook(self, id:int):
                step_postfix_hook.hook(id)

        class plain_error_hook:
            def hook(self, id:int):
                return int(error_hook.hook(id).value)

        _loop_hook = loop_hook
        if _loop_hook is not None:
            assert isinstance(_loop_hook, SnippetLoopHook), "loop_hook must be LoopHook instance"
            _loop_hook = plain_loop_hook()

        _step_prefix_hook = step_prefix_hook
        if _step_prefix_hook is not None:
            assert isinstance(_step_prefix_hook, SnippetStepHook), "step_prefix_hook must be StepHook instance"
            _step_prefix_hook = plain_prefix_step_hook()

        _step_postfix_hook = step_postfix_hook
        if _step_postfix_hook is not None:
            assert isinstance(_step_postfix_hook, SnippetStepHook), "step_postfix_hook must be StepHook instance"
            _step_postfix_hook = plain_step_postfix_hook()

        _error_hook = error_hook
        if _error_hook is not None:
            assert isinstance(_error_hook, SnippetStepErrorHook), "error_hook must be StepErrorHook instance"
            _error_hook = plain_error_hook()

        shared = cond.shared_objects
        cond = {'sourcecodestr':code,
                'total_timeout_sec':cond.total_timeout_sec,
                'dynamic_import':cond.dynamic_import,
                'allow_global_functions':cond.allow_global_functions,
                'allow_import_modules':cond.allow_import_modules}
        features = {'frequency':frequency,
                    'throttling_mode':throttling_mode,
                    'max_loop_timeout':max_loop_timeout,
                    'max_outer_loop_count':max_outer_loop_count,
                    'max_inner_loop_count':max_inner_loop_count,
                    'includes_comp_loop':includes_comp_loop,
                    'forced_execution_mode':forced_execution_mode}
        hooks = {'loop_hook':_loop_hook,
                 'step_prefix_hook':_step_prefix_hook,
                 'step_postfix_hook':_step_postfix_hook,
                 'error_hook':_error_hook}
        
        shared_object = {'shared':shared, 'hooks':hooks}
        configure_object = {'cond':cond, 'features':features}
        
        log_hook = None
        if self.debug_mode:
            logger = self.logger if self.logger else getLogger(__name__)
            class MyCommunicationLog(CommunicationLog):
                def log(self, tag, command, dump):
                    logger.debug(f'LOG: {tag} - {command}')
            log_hook = logger if isinstance(logger,CommunicationLog) else MyCommunicationLog()

        client = Communicator(connection=self.connection, 
                              sync_frequency=self.sync_frequency,
                              use_compress=not self.debug_mode,
                              log_hook=log_hook)

        client.client(shared_object=shared_object, 
                      configure_object=configure_object, 
                      conflict=self.sync_conflict_policy,
                      snippet_share_only=self.sync_snippet_share_only,
                      dump_object_depth=self.sync_shared_depth)