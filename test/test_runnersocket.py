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
from remoteexec.remoteexec import SnippetRunnerRemote
from remoteexec.communicate.exceptions import *
from remoteexec import *

def get_runner():
    def start_docker():
        subprocess.run(['docker', 'run', '-i', '--rm', '-p9165:9165', 'remoteexec:latest', 'python','-u', 'server.py', '--sync_frequency', '5', '--listen_addr', '0.0.0.0'])
    running_thread = threading.Thread(target=start_docker)
    running_thread.start()
    time.sleep(1) # wait to docker
    return remoteexec.SnippetRunner.run_tcp('localhost'), running_thread

class TestSocket:
    @pytest.fixture
    def init_instance(self):
        subprocess.run("cd docker; make", shell=True)

    def test__simple_append(self, init_instance):
        runner, running_thread = get_runner()
        cond = RunningConditions()
        code = dedent("""\
        a = 1
        b = 1
        c = a+b
        """)
        runner.exec(code, cond)
        running_thread.join()
        time.sleep(1) # wait to release port
    
    def test__shared_objects(self, init_instance):
        runner, running_thread = get_runner()
        share = {'hoge':1,'boo':'huu','foo':{}}
        cond = RunningConditions(shared_objects=share)
        code = dedent("""\
        a = hoge + 10
        b = boo
        foo['result'] = f'{a}{b}'
        time.sleep(1) # wait to sync
        """)
        runner.exec(code, cond)
        assert share['foo']=={'result':'11huu'}
        running_thread.join()
        time.sleep(1) # wait to release port

    def test__shared_objects_error(self, init_instance):
        runner, running_thread = get_runner()
        share = {'hoge':1,'boo':'huu','foo':{}}
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
        except ExceptionInServerError as e:
            assert str(e) == "NameError()"
        running_thread.join()
        time.sleep(1) # wait to release port

    def test__dynamic_import(self, init_instance):
        runner, running_thread = get_runner()
        cond = RunningConditions(dynamic_import=True, allow_import_modules=[])
        code = dedent("""\
        import time
        time.time()
        """)
        runner.exec(code, cond)
        running_thread.join()
        time.sleep(1) # wait to release port

    def test__dynamic_import_error(self, init_instance):
        runner, running_thread = get_runner()
        cond = RunningConditions(dynamic_import=False, allow_import_modules=[])
        code = dedent("""\
        import time
        time.time()
        """)
        try:
            runner.exec(code, cond)
            assert False
        except ExceptionInServerError as e:
            assert str(e) == "NameError()"
        running_thread.join()
        time.sleep(1) # wait to release port

    def test__allow_global_functions(self, init_instance):
        runner, running_thread = get_runner()
        cond = RunningConditions(allow_global_functions=['int'])
        code = dedent("""\
        a = int(10)
        """)
        runner.exec(code, cond)
        running_thread.join()
        time.sleep(1) # wait to release port

    def test__allow_global_functions_error(self, init_instance):
        runner, running_thread = get_runner()
        cond = RunningConditions(allow_global_functions=['int'])
        code = dedent("""\
        a = float(10)
        """)
        try:
            runner.exec(code, cond)
            assert False
        except ExceptionInServerError as e:
            assert str(e) == "NameError()"
        running_thread.join()
        time.sleep(1) # wait to release port

    def test__allow_import_modules(self, init_instance):
        runner, running_thread = get_runner()
        cond = RunningConditions(allow_import_modules=['time'])
        code = dedent("""\
        time.time()
        """)
        runner.exec(code, cond)
        running_thread.join()
        time.sleep(1) # wait to release port

    def test__notallow_import_modules(self, init_instance):
        runner, running_thread = get_runner()
        cond = RunningConditions(allow_import_modules=[])
        code = dedent("""\
        time.time()
        """)
        try:
            runner.exec(code, cond)
            assert False
        except ExceptionInServerError as e:
            assert str(e) == "NameError()"
        running_thread.join()
        time.sleep(1) # wait to release port
