import pytest
import subprocess
from subprocess import PIPE, Popen
from typing import List, Dict, Tuple, Union, Callable, Optional
from textwrap import dedent
import time
import threading
from remoteexec import *
from remoteexec.hooks import *
from remoteexec.exceptions import *

class TestRunningConditions:
    @pytest.fixture
    def init_instance(self):
        pass

    def test__simple_append(self, init_instance):
        runner = SnippetRunner(local_run=True)
        cond = RunningConditions()
        code = dedent("""\
        a = 1
        b = 1
        c = a+b
        """)
        runner.exec(code, cond)
    
    def test__shared_objects(self, init_instance):
        share = {'hoge':1,'boo':'huu','foo':{}}
        runner = SnippetRunner(local_run=True)
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
        runner = SnippetRunner(local_run=True)
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
        runner = SnippetRunner(local_run=True)
        cond = RunningConditions(dynamic_import=True, allow_import_modules=[])
        code = dedent("""\
        import time
        time.time()
        """)
        runner.exec(code, cond)

    def test__dynamic_import_error(self, init_instance):
        runner = SnippetRunner(local_run=True)
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
        runner = SnippetRunner(local_run=True)
        cond = RunningConditions(allow_global_functions=['int'])
        code = dedent("""\
        a = int(10)
        """)
        runner.exec(code, cond)

    def test__allow_global_functions_error(self, init_instance):
        runner = SnippetRunner(local_run=True)
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
        runner = SnippetRunner(local_run=True)
        cond = RunningConditions(allow_import_modules=['time'])
        code = dedent("""\
        time.time()
        """)
        runner.exec(code, cond)

    def test__notallow_import_modules(self, init_instance):
        runner = SnippetRunner(local_run=True)
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
        runner = SnippetRunner(local_run=True)
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
        runner = SnippetRunner(local_run=True)
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
        runner = SnippetRunner(local_run=True)
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


class TestRunningHooks:
    @pytest.fixture
    def init_instance(self):
        pass

    def test__RunningWithSteppingCheck(self, init_instance):
        share = {'hoge':[]}
        runner = SnippetRunner(local_run=True)
        class MyPrefixHook(StepHook):
            def __init__(self):
                super().__init__([])
            def hook(self, id:int, lineno:int):
                share['hoge'].append(f"MyPrefixHook - {lineno}")
        class MyPostfixHook(StepHook):
            def __init__(self):
                super().__init__([])
            def hook(self, id:int, lineno:int):
                share['hoge'].append(f"MyPostfixHook - {lineno}")
        cond = RunningConditions(shared_objects=share)
        code = dedent("""\
        hoge.append(1)
        hoge.append(2)
        hoge.append(3)
        """)
        runner.exec(code, cond=cond, step_prefix_hook=MyPrefixHook(), step_postfix_hook=MyPostfixHook())
        assert share['hoge'] == ['MyPrefixHook - 1', 1, 'MyPostfixHook - 1', 'MyPrefixHook - 2', 2, 'MyPostfixHook - 2', 'MyPrefixHook - 3', 3, 'MyPostfixHook - 3']

    def test__RunningWithSteppingCheckLoop(self, init_instance):
        share = {'hoge':[]}
        runner = SnippetRunner(local_run=True)
        cond = RunningConditions(shared_objects=share)
        class MyPrefixHook(StepHook):
            def __init__(self):
                super().__init__([])
            def hook(self, id:int, lineno:int):
                share['hoge'].append(f"MyPrefixHook - {lineno}")
        class MyPostfixHook(StepHook):
            def __init__(self):
                super().__init__([])
            def hook(self, id:int, lineno:int):
                share['hoge'].append(f"MyPostfixHook - {lineno}")
        code = dedent("""\
        for i in range(3):
            hoge.append(1)
        """)
        runner.exec(code, cond=cond, step_prefix_hook=MyPrefixHook(), step_postfix_hook=MyPostfixHook())
        assert share['hoge'] == ['MyPrefixHook - 1', 'MyPrefixHook - 2', 1, 'MyPostfixHook - 2', 'MyPrefixHook - 2', 1, 'MyPostfixHook - 2', 'MyPrefixHook - 2', 1, 'MyPostfixHook - 2', 'MyPostfixHook - 1']

    def test__RunningWithIgnoreError(self, init_instance):
        share = {'hoge':[]}
        runner = SnippetRunner(local_run=True)
        cond = RunningConditions(shared_objects=share)
        code = dedent("""\
        for i in range(3):
            hoge.append('start')
            hoge.append(100 / 0)  # raise error
            hoge.append('end')
        """)
        class _StepErrorHook(StepErrorHook):
            def __init__(self, error_approach):
                super().__init__(targets=[])
                self.error_approach = error_approach
            def hook(self, id:int, lineno:int) -> StepErrorApproach:
                return self.error_approach
        runner.exec(code, cond=cond, error_hook=_StepErrorHook(StepErrorApproach.IGNORE_AND_CONTINUE))
        assert share['hoge'] == ['start','end'] * 3
        runner.exec(code, cond=cond, error_hook=_StepErrorHook(StepErrorApproach.IGNORE_AND_BREAK))
        assert share['hoge'] == ['start','end'] * 3 + ['start'] * 3
        try:
            runner.exec(code, cond=cond, error_hook=_StepErrorHook(StepErrorApproach.DEFAULT))
            assert False
        except ZeroDivisionError:
            pass
        try:
            runner.exec(code, cond=cond, error_hook=_StepErrorHook(StepErrorApproach.RAISE_ERROR))
            assert False
        except SnippetStepError:
            pass

    def test__RunningWithLoopHook(self, init_instance):
        share = {'hoge':[]}
        runner = SnippetRunner(local_run=True)
        cond = RunningConditions(shared_objects=share)
        code = dedent("""\
        for i in range(500):
            hoge.append('hoge')
        """)
        runner.exec(code, cond=cond, max_outer_loop_count=5, throttling_mode=False, forced_execution_mode=True)
        assert share['hoge'] == ['hoge'] * 5

    def test__RunningWithLoopHookMulti(self, init_instance):
        share = {'hoge':[]}
        runner = SnippetRunner(local_run=True)
        cond = RunningConditions(shared_objects=share)
        code = dedent("""\
        for i in range(500):
            hoge.append('foo')
            for j in range(500):
                hoge.append('buu')
        """)
        runner.exec(code, cond=cond, max_outer_loop_count=2, max_inner_loop_count=2, throttling_mode=False, forced_execution_mode=True)
        assert share['hoge'] == ['foo', 'buu', 'buu'] * 2

    def test__RunningWithOuterFrequency(self, init_instance):
        share = {'hoge':[]}
        runner = SnippetRunner(local_run=True)
        cond = RunningConditions(shared_objects=share)
        code = dedent("""\
        for i in range(500):
            if i%100==0:
                hoge.append('hoge')
        """)
        start_time = time.time()
        runner.exec(code, cond=cond, frequency=50)
        assert int(round(time.time() - start_time)) == 10
        assert share['hoge'] == ['hoge'] * 5

    def test__RunningWithOuterFrequencyNoThrottling(self, init_instance):
        share = {'hoge':[]}
        runner = SnippetRunner(local_run=True)
        cond = RunningConditions(shared_objects=share)
        code = dedent("""\
        for i in range(500):
            if i%100==0:
                hoge.append('hoge')
        """)
        start_time = time.time()
        runner.exec(code, cond=cond, frequency=50, throttling_mode=False)
        assert int(round(time.time() - start_time)) < 1
        assert share['hoge'] == ['hoge'] * 5

    def test__RunningWithOuterFrequencyMax_outer_loop_count(self, init_instance):
        share = {'hoge':[]}
        runner = SnippetRunner(local_run=True)
        cond = RunningConditions(shared_objects=share)
        code = dedent("""\
        for i in range(500):
            if i%100==0:
                hoge.append('hoge')
        """)
        start_time = time.time()
        runner.exec(code, cond=cond, frequency=10, max_outer_loop_count=100, forced_execution_mode=True)
        assert int(round(time.time() - start_time)) == 10
        assert share['hoge'] == ['hoge']

