import sys, os, subprocess
from typing import List, Dict, Tuple, Union, Callable, Optional
import types
import socket
import json
import time
import queue
import ctypes
import threading
from ..remoteexec import *
from ..communicate import *
from ..communicate.serializer import loads, dumps
from ..communicate.sync import *
from ..communicate.exceptions import *
from ..hooks import *


class ConsoleIO(CommunicationIO):
    def __init__(self, f1, f2):
        self.f1 = f1
        self.f2 = f2
    def send(self, data:bytearray)->int:
        n = self.f1.write(data.decode('UTF-8'))
        self.f1.flush()
        return n
    def recv(self, delimiter:bytes=b'\n')->bytearray:
        line = self.f2.readline()
        return line.encode('UTF-8')
    def close(self):
        pass

class SocketIO(CommunicationIO):
    def __init__(self, listen_port, listen_addr):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((listen_addr, listen_port))
        self.socket.listen(1)
        client, _ = self.socket.accept()
        self.reader = client.makefile('rw')
    def send(self, data:bytearray)->int:
        n = self.reader.write(data.decode('UTF-8'))
        self.reader.flush()
    def recv(self, delimiter:bytes=b'\n')->bytearray:
        line = self.reader.readline()
        return line.encode('UTF-8')
    def close(self):
        self.reader.close()
        self.socket.close()

class PipeIO(CommunicationIO):
    def __init__(self, popen_command):
        self.task = Popen(popen_command, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    def send(self, data:bytearray)->int:
        n = self.task.stdin.write(data)
        self.task.stdin.flush()
        return n
    def recv(self, delimiter:bytes=b'\n')->bytearray:
        r = self.task.stdout.readline()
        if r == b'':
            raise SnippetAbortException()
        return r
    def close(self):
        self.task.terminate()
        self.task.wait()

class SocketReciever(CommunicationInterface):
    def __init__(self, sync_hook=None):
        self.shared_object = None
        self.sourcecodestr = None
        self.total_timeout_sec = 0
        self.dynamic_import = False
        self.allow_global_functions = []
        self.allow_import_modules = []
        self.feature_hooks = {'loop_hook':None,'step_prefix_hook':None,'step_postfix_hook':None,'error_hook':None}
        self.running_features = []
        self.sync_hook = sync_hook
        self.runner = None
        self.running_thread = None

    def init_share_object(self, share_object):
        self.shared_object = share_object['shared']
        self.feature_hooks = share_object['hooks']

    def init_configure_object(self, configure_object):
        self.sourcecodestr = configure_object['cond']['sourcecodestr']
        self.total_timeout_sec = configure_object['cond']['total_timeout_sec']
        self.dynamic_import = configure_object['cond']['dynamic_import']
        self.allow_global_functions = configure_object['cond']['allow_global_functions']
        self.allow_import_modules = configure_object['cond']['allow_import_modules']

        features = configure_object['features']

        class MyLoopHook(LoopHook):
            def hook(self, id:int, lineno:int):
                self.feature_hooks['loop_hook'].hook(id=id, lineno=lineno)
            def clear_loop(self, id:int):
                self.feature_hooks['loop_hook'].clear_loop(id=id)

        self.running_features = []
        if features['frequency'] > 0 or features['throttling_mode']==False:
            loophookfeature = RunningWithOuterFrequency(frequency=features['frequency'],
                                                        throttling_mode=features['throttling_mode'],
                                                        max_loop_timeout=features['max_loop_timeout'],
                                                        max_outer_loop_count=features['max_outer_loop_count'],
                                                        max_inner_loop_count=features['max_inner_loop_count'],
                                                        includes_comp_loop=features['includes_comp_loop'],
                                                        forced_execution_mode=features['forced_execution_mode'])
            if self.feature_hooks['loop_hook'] is not None:
                loophookfeature.extra_hooks.append(MyLoopHook())
            self.running_features.append(loophookfeature)
        elif self.feature_hooks['loop_hook'] is not None:
            self.running_features.append(RunningWithLoopHook(MyLoopHook))

        if self.feature_hooks['step_prefix_hook'] is not None or\
           self.feature_hooks['step_postfix_hook'] is not None or\
           self.feature_hooks['error_hook'] is not None:
            class MyPrefixHook(StepHook):
                def hook(self, id:int, lineno:int):
                    self.feature_hooks['step_prefix_hook'].hook(id=id, lineno=lineno)
            class MyPostfixHook(StepHook):
                def hook(self, id:int, lineno:int):
                    self.feature_hooks['step_postfix_hook'].hook(id=id, lineno=lineno)
            class MyErrorHook(StepErrorHook):
                def hook(self, id:int, lineno:int) -> StepErrorApproach:
                    return StepErrorApproach(self.feature_hooks['error_hook'].hook(id=id, lineno=lineno))
            self.running_features.append(RunningWithSteppingCheck(prefix_hook_class=MyPrefixHook if self.feature_hooks['step_prefix_hook'] is not None else None,
                                                                  postfix_hook_class=MyPostfixHook if self.feature_hooks['step_postfix_hook'] is not None else None,
                                                                  error_hook_class=MyErrorHook if self.feature_hooks['error_hook'] is not None else None))

    def start_command(self):
        self.runner = SnippetRunnerLocal()
        cond = RunningConditions(shared_objects=self.shared_object,
                                 total_timeout_sec=self.total_timeout_sec,
                                 dynamic_import=self.dynamic_import,
                                 allow_global_functions=self.allow_global_functions,
                                 allow_import_modules=self.allow_import_modules)
        the_thread_id = threading.current_thread().ident
        def run_start():
            try:
                self.runner.exec(self.sourcecodestr,
                                cond=cond,
                                features=self.running_features)
            except Exception as e:
                try:
                    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(the_thread_id),
                                                        ctypes.py_object(e.__class__))
                    if res == 0:
                        raise ValueError("thread state error")
                    elif res != 1:
                        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(the_thread_id), None)
                        raise SystemError("senf exception error")
                except Exception:
                    pass

        self.running_thread = threading.Thread(target=run_start)
        self.running_thread.start()

    def is_alive(self):
        if self.shared_object is not None and self.sync_hook is not None:
            self.sync_hook(self.shared_object)
        if self.running_thread is not None:
            return self.running_thread.is_alive()
        return self.runner is None

    def stop(self):
        pass

