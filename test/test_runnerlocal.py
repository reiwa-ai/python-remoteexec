import pytest
import subprocess
from subprocess import PIPE, Popen
from typing import List, Dict, Tuple, Union, Callable, Optional
from textwrap import dedent
import time
import threading
import remoteexec
from remoteexec.hooks import *
from remoteexec.exceptions import *
from remoteexec.runnerfeature import *
from remoteexec.remoteexec import SnippetRunnerLocal
from remoteexec import *

class TestRunningConditions:
    @pytest.fixture
    def init_instance(self):
        pass

    def test__simple_append(self, init_instance):
        runner = SnippetRunnerLocal()
        cond = RunningConditions()
        code = dedent("""\
        a = 1
        b = 1
        c = a+b
        """)
        runner.exec(code, cond)
    
    def test__shared_objects(self, init_instance):
        share = {'hoge':1,'boo':'huu','foo':{}}
        runner = SnippetRunnerLocal()
        cond = RunningConditions(shared_objects=share)
        code = dedent("""\
        a = hoge + 10
        b = boo
        foo['result'] = f'{a}{b}'
        """)
        runner.exec(code, cond)
        assert share['foo']=={'result':'11huu'}
    
    def test__shared_objects_error(self, init_instance):
        share = {'hoge':1,'boo':'huu','foo':{}}
        runner = SnippetRunnerLocal()
        cond = RunningConditions(shared_objects=share)
        code = dedent("""\
        a = hoge + 10
        b = boo
        c = hogehoge
        foo['result'] = f'{a}{b}'
        """)
        try:
            runner.exec(code, cond)
            assert False
        except NameError:
            pass

    def test__dynamic_import(self, init_instance):
        runner = SnippetRunnerLocal()
        cond = RunningConditions(dynamic_import=True, allow_import_modules=[])
        code = dedent("""\
        import time
        time.time()
        """)
        runner.exec(code, cond)

    def test__dynamic_import_error(self, init_instance):
        runner = SnippetRunnerLocal()
        cond = RunningConditions(dynamic_import=False, allow_import_modules=[])
        code = dedent("""\
        import time
        time.time()
        """)
        try:
            runner.exec(code, cond)
            assert False
        except NameError:
            pass

    def test__allow_global_functions(self, init_instance):
        runner = SnippetRunnerLocal()
        cond = RunningConditions(allow_global_functions=['int'])
        code = dedent("""\
        a = int(10)
        """)
        runner.exec(code, cond)

    def test__allow_global_functions_error(self, init_instance):
        runner = SnippetRunnerLocal()
        cond = RunningConditions(allow_global_functions=['int'])
        code = dedent("""\
        a = float(10)
        """)
        try:
            runner.exec(code, cond)
            assert False
        except NameError:
            pass

    def test__allow_import_modules(self, init_instance):
        runner = SnippetRunnerLocal()
        cond = RunningConditions(allow_import_modules=['time'])
        code = dedent("""\
        time.time()
        """)
        runner.exec(code, cond)

    def test__notallow_import_modules(self, init_instance):
        runner = SnippetRunnerLocal()
        cond = RunningConditions(allow_import_modules=[])
        code = dedent("""\
        time.time()
        """)
        try:
            runner.exec(code, cond)
            assert False
        except NameError:
            pass

    def test__timeout_error(self, init_instance):
        runner = SnippetRunnerLocal()
        cond = RunningConditions(allow_import_modules=['time'], total_timeout_sec=0.5)
        code = dedent("""\
        for _ in range(1000):
            time.sleep(0.01)
        """)
        start_time = time.time()
        end_time = 0
        try:
            runner.exec(code, cond)
            assert False
        except SnippetTotalTimeout:
            end_time = time.time()
            pass
        assert round((end_time - start_time)*10) == 5

    def test__longtimeout_error(self, init_instance):
        runner = SnippetRunnerLocal()
        cond = RunningConditions(allow_import_modules=['time'], total_timeout_sec=0.5)
        code = dedent("""\
        time.sleep(10)
        """)
        start_time = time.time()
        end_time = 0
        try:
            runner.exec(code, cond)
            assert False
        except SnippetTotalTimeout:
            end_time = time.time()
            pass
        assert round((end_time - start_time)*10) == 5

    def test__timeoutthread_error(self, init_instance):
        runner = SnippetRunnerLocal()
        cond = RunningConditions(allow_import_modules=['time'], total_timeout_sec=0.5)
        code = dedent("""\
        while True:
            time.sleep(0.01)
        """)
        def run_start():
            nonlocal end_time
            try:
                runner.exec(code, cond)
                assert False
            except SnippetTotalTimeout:
                end_time = time.time()
                pass
        thread = threading.Thread(target=run_start)
        start_time = time.time()
        end_time = 0
        thread.start()
        time.sleep(1)
        assert not thread.is_alive()
        thread.join()
        assert not thread.is_alive()
        assert round((end_time - start_time)*10) == 5


class TestRunningFeatures:
    @pytest.fixture
    def init_instance(self):
        pass

    def test__RunningWithSteppingCheck(self, init_instance):
        share = {'hoge':[]}
        runner = SnippetRunnerLocal()
        cond = RunningConditions(shared_objects=share)
        class MyPrefixHook(StepHook):
            def hook(self, id:int, lineno:int):
                share['hoge'].append(f"MyPrefixHook - {lineno}")
        class MyPostfixHook(StepHook):
            def hook(self, id:int, lineno:int):
                share['hoge'].append(f"MyPostfixHook - {lineno}")
        feature = RunningWithSteppingCheck(prefix_hook_class=MyPrefixHook, postfix_hook_class=MyPostfixHook)
        code = dedent("""\
        hoge.append(1)
        hoge.append(2)
        hoge.append(3)
        """)
        runner = SnippetRunnerLocal()
        runner.exec(code, cond=cond, features=[feature])
        assert share['hoge'] == ['MyPrefixHook - 1', 1, 'MyPostfixHook - 1', 'MyPrefixHook - 2', 2, 'MyPostfixHook - 2', 'MyPrefixHook - 3', 3, 'MyPostfixHook - 3']

    def test__RunningWithSteppingCheckLoop(self, init_instance):
        share = {'hoge':[]}
        runner = SnippetRunnerLocal()
        cond = RunningConditions(shared_objects=share)
        class MyPrefixHook(StepHook):
            def hook(self, id:int, lineno:int):
                share['hoge'].append(f"MyPrefixHook - {lineno}")
        class MyPostfixHook(StepHook):
            def hook(self, id:int, lineno:int):
                share['hoge'].append(f"MyPostfixHook - {lineno}")
        feature = RunningWithSteppingCheck(prefix_hook_class=MyPrefixHook, postfix_hook_class=MyPostfixHook)
        code = dedent("""\
        for i in range(3):
            hoge.append(1)
        """)
        runner = SnippetRunnerLocal()
        runner.exec(code, cond=cond, features=[feature])
        assert share['hoge'] == ['MyPrefixHook - 1', 'MyPrefixHook - 2', 1, 'MyPostfixHook - 2', 'MyPrefixHook - 2', 1, 'MyPostfixHook - 2', 'MyPrefixHook - 2', 1, 'MyPostfixHook - 2', 'MyPostfixHook - 1']

    def test__RunningWithIgnoreError(self, init_instance):
        share = {'hoge':[]}
        runner = SnippetRunnerLocal()
        cond = RunningConditions(shared_objects=share)
        code = dedent("""\
        for i in range(3):
            hoge.append('start')
            hoge.append(100 / 0)  # raise error
            hoge.append('end')
        """)
        feature = RunningWithIgnoreError(StepErrorApproach.IGNORE_AND_CONTINUE)
        runner.exec(code, cond=cond, features=[feature])
        assert share['hoge'] == ['start','end'] * 3
        feature = RunningWithIgnoreError(StepErrorApproach.IGNORE_AND_BREAK)
        runner.exec(code, cond=cond, features=[feature])
        assert share['hoge'] == ['start','end'] * 3 + ['start'] * 3
        try:
            feature = RunningWithIgnoreError(StepErrorApproach.DEFAULT)
            runner.exec(code, cond=cond, features=[feature])
            assert False
        except ZeroDivisionError:
            pass
        try:
            feature = RunningWithIgnoreError(StepErrorApproach.RAISE_ERROR)
            runner.exec(code, cond=cond, features=[feature])
            assert False
        except SnippetStepError:
            pass

    def test__RunningWithEvalCheck(self, init_instance):
        share = {'hoge':[]}
        runner = SnippetRunnerLocal()
        cond = RunningConditions(shared_objects=share, allow_global_functions=['eval'])
        class MyStepTargetHook(StepTargetHook):
            def hook(self, id:int, lineno:int) -> Optional[List[str]]:
                return ["target"] if lineno==2 or lineno==4 else None
        class MyStepEvalHook(StepEvalHook):
            def hook(self, id:int, lineno:int, name:str, value:Optional[object]):
                share['hoge'].append(f"StepEvalHook -- lineno={lineno} name={name} value={value}")
        feature = RunningWithEvalCheck(target_hook_class=MyStepTargetHook,
                                   eval_hook_class=MyStepEvalHook)
        code = dedent("""\
        target = "abcde"
        hoge.append('start')
        hoge.append(target:='fghij')
        hoge.append('end')
        """)
        runner.exec(code, cond=cond, features=[feature])
        assert share['hoge'] == ['start','StepEvalHook -- lineno=2 name=target value=abcde','fghij','end','StepEvalHook -- lineno=4 name=target value=fghij']

    def test__RunningWithLoopHook(self, init_instance):
        share = {'hoge':[]}
        runner = SnippetRunnerLocal()
        cond = RunningConditions(shared_objects=share)
        class MyCounterLoopHook(CounterLoopHook):
           def __init__(self, loops:List[HookTarget]):
               super().__init__(loops=loops, maxcount=5)
        feature = RunningWithLoopHook([MyCounterLoopHook], forced_execution_mode=True)
        code = dedent("""\
        for i in range(500):
            hoge.append('hoge')
        """)
        runner.exec(code, cond=cond, features=[feature])
        assert share['hoge'] == ['hoge'] * 5

    def test__RunningWithLoopHookMulti(self, init_instance):
        share = {'hoge':[]}
        runner = SnippetRunnerLocal()
        cond = RunningConditions(shared_objects=share)
        class MyCounterLoopHook(CounterLoopHook):
           def __init__(self, loops:List[HookTarget]):
               super().__init__(loops=loops, maxcount=2)
        feature = RunningWithLoopHook([MyCounterLoopHook], forced_execution_mode=True)
        code = dedent("""\
        for i in range(500):
            hoge.append('foo')
            for j in range(500):
                hoge.append('buu')
        """)
        runner.exec(code, cond=cond, features=[feature])
        assert share['hoge'] == ['foo', 'buu', 'buu'] * 2

    def test__RunningWithOuterFrequency(self, init_instance):
        share = {'hoge':[]}
        runner = SnippetRunnerLocal()
        cond = RunningConditions(shared_objects=share)
        feature = RunningWithOuterFrequency(frequency=50)
        code = dedent("""\
        for i in range(500):
            if i%100==0:
                hoge.append('hoge')
        """)
        start_time = time.time()
        runner.exec(code, cond=cond, features=[feature])
        assert int(round(time.time() - start_time)) == 10
        assert share['hoge'] == ['hoge'] * 5

    def test__RunningWithOuterFrequencyNoThrottling(self, init_instance):
        share = {'hoge':[]}
        runner = SnippetRunnerLocal()
        cond = RunningConditions(shared_objects=share)
        feature = RunningWithOuterFrequency(frequency=50, throttling_mode=False)
        code = dedent("""\
        for i in range(500):
            if i%100==0:
                hoge.append('hoge')
        """)
        start_time = time.time()
        runner.exec(code, cond=cond, features=[feature])
        assert int(round(time.time() - start_time)) < 1
        assert share['hoge'] == ['hoge'] * 5

    def test__RunningWithOuterFrequencyMax_outer_loop_count(self, init_instance):
        share = {'hoge':[]}
        runner = SnippetRunnerLocal()
        cond = RunningConditions(shared_objects=share)
        feature = RunningWithOuterFrequency(frequency=10, max_outer_loop_count=100, forced_execution_mode=True)
        code = dedent("""\
        for i in range(500):
            if i%100==0:
                hoge.append('hoge')
        """)
        start_time = time.time()
        runner.exec(code, cond=cond, features=[feature])
        assert int(round(time.time() - start_time)) == 10
        assert share['hoge'] == ['hoge']


    def test__RunningWithIgnoreErrorAndLoopHook(self, init_instance):
        share = {'hoge':[]}
        runner = SnippetRunnerLocal()
        cond = RunningConditions(shared_objects=share)
        class MyCounterLoopHook(CounterLoopHook):
           def __init__(self, loops:List[HookTarget]):
               super().__init__(loops=loops, maxcount=5)
        feature1 = RunningWithLoopHook([MyCounterLoopHook], forced_execution_mode=True)
        feature2 = RunningWithIgnoreError(StepErrorApproach.IGNORE_AND_CONTINUE)
        code = dedent("""\
        for i in range(500):
            hoge.append('boo')
            hoge.append(10/0)
            hoge.append('foo')
        """)
        runner.exec(code, cond=cond, features=[feature1,feature2])
        assert share['hoge'] == ['boo','foo'] *5
        feature2 = RunningWithIgnoreError(StepErrorApproach.IGNORE_AND_BREAK)
        code = dedent("""\
        for i in range(500):
            hoge.append('boo')
            hoge.append(10/0)
            hoge.append('foo')
        """)
        runner.exec(code, cond=cond, features=[feature1,feature2])
        assert share['hoge'] == ['boo','foo'] *5 + ['boo'] * 5

    def test__RunningWithIgnoreErrorAndOuterFrequency(self, init_instance):
        share = {'hoge':[]}
        runner = SnippetRunnerLocal()
        cond = RunningConditions(shared_objects=share)
        class MyCounterLoopHook(CounterLoopHook):
           def __init__(self, loops:List[HookTarget]):
               super().__init__(loops=loops, maxcount=5)
        feature1 = RunningWithOuterFrequency(frequency=50)
        feature2 = RunningWithIgnoreError(StepErrorApproach.IGNORE_AND_CONTINUE)
        code = dedent("""\
        for i in range(500):
            if i%100==0:
                hoge.append('boo')
                hoge.append(10/0)
                hoge.append('foo')
        """)
        start_time = time.time()
        runner.exec(code, cond=cond, features=[feature1,feature2])
        assert int(round(time.time() - start_time)) == 10
        assert share['hoge'] == ['boo','foo'] *5
        feature2 = RunningWithIgnoreError(StepErrorApproach.IGNORE_AND_BREAK)
        start_time = time.time()
        runner.exec(code, cond=cond, features=[feature1,feature2])
        assert int(round(time.time() - start_time)) == 10
        assert share['hoge'] == ['boo','foo'] *5 + ['boo'] * 5

    def test__RunningWithSteppingCheckAndLoopHook(self, init_instance):
        share = {'hoge':[]}
        runner = SnippetRunnerLocal()
        cond = RunningConditions(shared_objects=share)
        class MyCounterLoopHook(CounterLoopHook):
           def __init__(self, loops:List[HookTarget]):
               super().__init__(loops=loops, maxcount=5)
        feature1 = RunningWithLoopHook([MyCounterLoopHook], forced_execution_mode=True)
        class MyPrefixHook(StepHook):
            def hook(self, id:int, lineno:int):
                share['hoge'].append(f"MyPrefixHook - {lineno}")
        class MyPostfixHook(StepHook):
            def hook(self, id:int, lineno:int):
                share['hoge'].append(f"MyPostfixHook - {lineno}")
        feature2 = RunningWithSteppingCheck(prefix_hook_class=MyPrefixHook, postfix_hook_class=MyPostfixHook)
        code = dedent("""\
        for i in range(500):
            hoge.append(1)
            hoge.append(2)
            hoge.append(3)
        """)
        runner = SnippetRunnerLocal()
        runner.exec(code, cond=cond, features=[feature1,feature2])
        assert share['hoge'] == ['MyPrefixHook - 1'] + \
                                ['MyPrefixHook - 2', 1, 'MyPostfixHook - 2', 'MyPrefixHook - 3', 2, 'MyPostfixHook - 3', 'MyPrefixHook - 4', 3, 'MyPostfixHook - 4']*5 + \
                                ['MyPostfixHook - 1']

    def test__RunningWithSteppingCheckAndOuterFrequency(self, init_instance):
        share = {'hoge':[]}
        runner = SnippetRunnerLocal()
        cond = RunningConditions(shared_objects=share)
        feature1 = RunningWithOuterFrequency(frequency=50)
        class MyPrefixHook(StepHook):
            def hook(self, id:int, lineno:int):
                share['hoge'].append(f"MyPrefixHook - {lineno}")
        class MyPostfixHook(StepHook):
            def hook(self, id:int, lineno:int):
                share['hoge'].append(f"MyPostfixHook - {lineno}")
        feature2 = RunningWithSteppingCheck(prefix_hook_class=MyPrefixHook, postfix_hook_class=MyPostfixHook)
        code = dedent("""\
        for i in range(500):
            hoge.append(1)
        """)
        runner = SnippetRunnerLocal()
        start_time = time.time()
        runner.exec(code, cond=cond, features=[feature1,feature2])
        assert int(round(time.time() - start_time)) == 10
        assert share['hoge'] == ['MyPrefixHook - 1'] +\
                                ['MyPrefixHook - 2', 1, 'MyPostfixHook - 2']*500 +\
                                ['MyPostfixHook - 1']
