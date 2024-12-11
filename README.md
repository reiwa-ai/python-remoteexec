# python-remoteexec-proj

## Remote execution environment for Python

This project is enviroment of REMOTE running Python code in Server or Docker.

The client sends code, shares objects on the server in real time and receives variables and function calls locally.

The goal is a secure sandbox. That includes code execution hooks, exception handling, limit execution times, and control loops frequency.


## Pythonコードのリモート実行環境

このプロジェクトは、サーバーやDockerコンテナ上で送信したPythonコードを遠隔実行する環境です。

クライアントはサーバー上のオブジェクトをリアルタイムで共有し、変数と関数呼び出しをローカルで受信します。

目的は安全なサンドボックスの構築です。これには、処理実行フック、例外処理対応、実行時間制限、ループ周波数制御が含まれます。


# Install

```sh
$ pip install remoteexec
```

or

```sh
$ pip install git+https://github.com/reiwa-ai/python-remoteexec
```


# Server Setup (see docker/scripts/server.py)

A program to wait for connections on a server that runs code.


```python
from remoteexec.communicate import *
from remoteexec.input import *

listen_addr = '1.1.1.1'
listen_port = 9165
sync_frequency = -1
fpS = SocketIO(listen_port=listen_port, listen_addr=listen_addr)
server = Communicator(connection=fpS, sync_frequency=sync_frequency, use_compress=True)
server.host(reciever=SocketReciever())
```


# Client side code


## Simple Usage

A program that sends code to a server and execute in server.


### run code in remote

```python
from remoteexec import *

connect_addr = '192.168.1.1'
connect_port = 9165
runner = SnippetRunner.run_tcp(connect_addr, connect_port)
cond = RunningConditions()

## Run code in server
code = """\
a = 1
b = 1
c = a+b
"""
runner.exec(code, cond)  # run in server
```


### share the object

```python
share = {'hoge':1,'boo':'huu','foo':{}}
cond = RunningConditions(shared_objects=share)
code = """\
a = hoge + 10
b = boo
foo['result'] = f'{a}{b}'
"""
runner.exec(code, cond)
print(share['foo']['result'])  ## display '11huu'
```


### call client side function from server

```python
import os
@snippet_share
class clz1:
    def __init__(self):
        self.n = ''
    def p(self):
        return print(self.n)

share = {'clz':clz1()}
cond = RunningConditions(shared_objects=share)
code = """\
clz.n = 'aaazzz'
clz.p()
"""
runner.exec(code, cond)  ## display 'aaazzz'
```


## Use as Sandbox

By default, built-in functions (exec globals) and import modules are not allowed.


### allow global functions (default not allowed)

```python
cond = RunningConditions(allow_global_functions=['int'])
code = dedent("""\
a = int(10)
""")
runner.exec(code, cond)
```


### allow import module (default not allowed)

```python
## Run code in server
cond = RunningConditions(dynamic_import=True, allow_import_modules=[])
code = """\
import time
"""
runner.exec(code, cond)
```

or

```python
cond = RunningConditions(allow_import_modules=['time'])
```


### safe builtins and modules

Built-in functions and standard packages that can be used without affecting OS filesystem. (ex. "range" is allowed but "open" is not allowed)

```python
cond = RunningConditions(allow_global_functions=COMMON_BUILTINS,
                         allow_import_modules=COMMON_MODULES)
```


### exception handling

Specify an error handling policy for each step execution.

Either ignore the error and continue executing the code anyway (IGNORE_AND_CONTINUE), turn the error into a loop break (IGNORE_AND_BREAK), raise a SnippetStepError (RAISE_ERROR), or just raise the error (the default).

**sample**

```python
from remoteexec.exceptions import *
from remoteexec.hooks import *

class _StepErrorHook(StepErrorHook):
    def __init__(self, error_approach):
        super().__init__(targets=[])
        self.error_approach = error_approach
    def hook(self, id:int, lineno:int) -> StepErrorApproach:
        return self.error_approach

## run code include error
code = """\
for i in range(3):
    hoge.append('start')
    hoge.append(100 / 0)  # raise error
    hoge.append('end')
"""

## ignore error and continue code running
share = {'hoge':[]}
cond = RunningConditions(shared_objects=share)
runner.exec(code, cond=cond, error_hook=_StepErrorHook(StepErrorApproach.IGNORE_AND_CONTINUE))
print(','.join(share['hoge']))  # display 'start,end,start,end,start,end'

## ignore error and break running code
share = {'hoge':[]}
cond = RunningConditions(shared_objects=share)
runner.exec(code, cond=cond, error_hook=_StepErrorHook(StepErrorApproach.IGNORE_AND_BREAK))
print(','.join(share['hoge']))  # display 'start,start,start'

## raise error
share = {'hoge':[]}
cond = RunningConditions(shared_objects=share)
runner.exec(code, cond=cond, error_hook=_StepErrorHook(StepErrorApproach.RAISE_ERROR))  # SnippetStepError

## transfar error
share = {'hoge':[]}
cond = RunningConditions(shared_objects=share)
runner.exec(code, cond=cond, error_hook=_StepErrorHook(StepErrorApproach.DEFAULT))  # ZeroDivisionError
```


## Controlling execution

Manage computing resources or limitate the number of executions.


### Maximum script execution time

```python
cond = RunningConditions(total_timeout_sec=0.5)  # Forced termination in 0.5 seconds
```


### Throttling loop run time

```python
runner.exec(code, cond=cond, frequency=50)  # loops force run at 50Hz
```

**sample**

```python
import time
share = {'hoge':[]}
cond = RunningConditions(shared_objects=share)
code = """\
for i in range(500):
    if i%100==0:
        hoge.append(f'{i}')
"""

## The loop runs at 50Hz in the server
start = time.time()
runner.exec(code, cond=cond, frequency=50)  # take 10 sec to run
print(time.time() - start)  # around 10
print(','.join(share['hoge']))  # display '0,100,200,300,400'
```


### Force limit loop execution times

The outermost loop can limit by max_outer_loop_count, and any nested loops can limit by max_inner_loop_count.

```python
## Raises a SnippetLoopOvertime exception when the loop execution count reaches the specified number.
runner.exec(code, cond=cond, max_outer_loop_count=2, max_inner_loop_count=3, throttling_mode=False)
```

```python
## Break the loop and continue running code when the loop execution count reaches the specified number.
runner.exec(code, cond=cond, max_outer_loop_count=2, max_inner_loop_count=3, throttling_mode=False, forced_execution_mode=True)
```


**sample**

```python
share = {'hoge':[]}
cond = RunningConditions(shared_objects=share)
code = """\
for i in range(500):
    hoge.append('foo')
    for j in range(500):
        hoge.append('buu')
"""
## Run code with forced limit loop exection number of 2 and 3
runner.exec(code, cond=cond, max_outer_loop_count=2, max_inner_loop_count=3, throttling_mode=False, forced_execution_mode=True)
print(','.join(share['hoge']))  # display 'foo,buu,buu,buu,foo,buu,buu,buu'
```


# Local Run

Local execution provides functionality for debugging code.


```python
from remoteexec import *
from remoteexec.runnerfeature import *
from remoteexec.hooks import *
runner_local = SnippetRunnerLocal()
cond = RunningConditions()
```

## Hooks

Interrupting and Managing Code Execution.


### Count loop repeatation

Count loop executed times.

**sample**

```python
class MyCounterLoopHook(CounterLoopHook):
    def __init__(self, loops:List[HookTarget]):
        super().__init__(loops=loops, maxcount=-1)
    def hook(self, id:int, lineno:int):
        def _hook():
            self.counter[id] += 1  # count loop executed times
            print(f"loop run {self.counter[id]} times")
        return _hook() if id in self.counter else super().hook(id=id, lineno=lineno)
feature = RunningWithLoopHook([MyCounterLoopHook], forced_execution_mode=True)
code = """\
a = 1
for _ in (1,2,3,4,5):
    a += 1
"""
runner_local.exec(code, cond=cond, features=[feature])
# loop run 1 times
# loop run 2 times
# loop run 3 times
# loop run 4 times
# loop run 5 times
```


### Breakpoint

Trace code execution.

**sample**

```python
class MyPrefixHook(StepHook):
    def hook(self, id:int, lineno:int):
        print(f"start - line #{lineno}")
class MyPostfixHook(StepHook):
    def hook(self, id:int, lineno:int):
        print(f"end - line #{lineno}")
feature = RunningWithSteppingCheck(prefix_hook_class=MyPrefixHook, postfix_hook_class=MyPostfixHook)
code = """\
a = 1
b = 2
c = 3
"""
runner_local.exec(code, cond=cond, features=[feature])
# start - line #1
# end - line #1
# start - line #2
# end - line #2
# start - line #3
# end - line #3
```


### Watching variables

Monitor variable assignments while your code is running.

**sample**

```python
share = {'hoge':[]}
cond = RunningConditions(shared_objects=share, allow_global_functions=['eval'])
## Returns the names of variables to watch for each row
class MyStepTargetHook(StepTargetHook):
    def hook(self, id:int, lineno:int) -> Optional[List[str]]:
        return ["target"] if lineno==2 or lineno==4 else None
## Monitor assignments to variables
class MyStepEvalHook(StepEvalHook):
    def hook(self, id:int, lineno:int, name:str, value:Optional[object]):
        print(f"lineno={lineno} name={name} value={value}")
feature = RunningWithEvalCheck(target_hook_class=MyStepTargetHook,
                               eval_hook_class=MyStepEvalHook)
code = """\
target = "abcde"
hoge.append('start')
hoge.append(target:='fghij')
hoge.append('end')
"""
runner_local.exec(code, cond=cond, features=[feature])
# lineno=2 name=target value=abcde
# lineno=4 name=target value=fghij
```


# Run in docker

If run it in a container or simply in a separate process, STDIN/OUT pipes can used instead of TCP.

see docker/Dockerfile and test/test_runnerdocker.py

## Container Side

Place the following script in the container with the name 'server.py'.

```python
import sys
from remoteexec.communicate import *
from remoteexec.input import *

sync_frequency = 5
fpS = ConsoleIO(sys.stdout, sys.stdin)
server = Communicator(connection=fpS, sync_frequency=sync_frequency, use_compress=True)
server.host(reciever=SocketReciever())
```


## Client Side

```python
runner = SnippetRunner.run_docker()
```

or

```python
from remoteexec.inout import *
connection = PipeIO(('docker', 'run', '-i', '--rm', 'dockercontainername', 'python', '-u', 'server.py'))
runner = SnippetRunnerRemote(connection=connection)
```

