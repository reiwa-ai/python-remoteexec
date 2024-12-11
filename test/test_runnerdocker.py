import pytest
import subprocess
from subprocess import PIPE, Popen
from typing import List, Dict, Tuple, Union, Callable, Optional
from textwrap import dedent
import time
import threading
import remoteexec
from remoteexec.inout import *
from remoteexec.hooks import *
from remoteexec.exceptions import *
from remoteexec.runnerfeature import *
from remoteexec.remoteexec import SnippetRunnerRemote
from remoteexec.communicate.exceptions import *
from remoteexec import *

class DockerCommunicationIO(PipeIO):
    def __init__(self, frequency=5):
        super().__init__(('docker', 'run', '-i', '--rm', 'remoteexec:latest', 'python','-u', 'server.py', '--sync_frequency', f'{frequency}'))

class TestDocker:
    @pytest.fixture
    def init_instance(self):
        subprocess.run("cd docker; make", shell=True)

    def test__docker_echo(self, init_instance):
        task = Popen(('docker', 'run', '-i', '--rm', 'remoteexec:latest', 'python','-u', 'echo.py'), stdin=PIPE, stdout=PIPE, stderr=PIPE)
        task.stdin.write(f'boo\n'.encode())
        task.stdin.flush()
        result = task.stdout.readline()
        assert result==b'boo\n'
        task.stdin.write(f'huu\n'.encode())
        task.stdin.flush()
        result = task.stdout.readline()
        assert result==b'huu\n'
        task.stdin.write(f'hogehoge\n'.encode())
        task.stdin.flush()
        result = task.stdout.readline()
        assert result==b'hogehoge\n'
        task.stdin.write(f'end\n'.encode())
        task.stdin.flush()
        task.terminate()
        task.wait()

    def test__simple_append(self, init_instance):
        connection = DockerCommunicationIO()
        runner = SnippetRunnerRemote(connection=connection)
        cond = RunningConditions()
        code = dedent("""\
        a = 1
        b = 1
        c = a+b
        """)
        runner.exec(code, cond)
    
    def test__shared_objects(self, init_instance):
        connection = DockerCommunicationIO()
        runner = SnippetRunnerRemote(connection=connection)
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
    
    def test__shared_objects_error(self, init_instance):
        connection = DockerCommunicationIO()
        runner = SnippetRunnerRemote(connection=connection)
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

    def test__dynamic_import(self, init_instance):
        connection = DockerCommunicationIO()
        runner = SnippetRunnerRemote(connection=connection)
        cond = RunningConditions(dynamic_import=True, allow_import_modules=[])
        code = dedent("""\
        import time
        time.time()
        """)
        runner.exec(code, cond)

    def test__dynamic_import_error(self, init_instance):
        connection = DockerCommunicationIO()
        runner = SnippetRunnerRemote(connection=connection)
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

    def test__allow_global_functions(self, init_instance):
        connection = DockerCommunicationIO()
        runner = SnippetRunnerRemote(connection=connection)
        cond = RunningConditions(allow_global_functions=['int'])
        code = dedent("""\
        a = int(10)
        """)
        runner.exec(code, cond)

    def test__allow_global_functions_error(self, init_instance):
        connection = DockerCommunicationIO()
        runner = SnippetRunnerRemote(connection=connection)
        cond = RunningConditions(allow_global_functions=['int'])
        code = dedent("""\
        a = float(10)
        """)
        try:
            runner.exec(code, cond)
            assert False
        except ExceptionInServerError as e:
            assert str(e) == "NameError()"

    def test__allow_import_modules(self, init_instance):
        connection = DockerCommunicationIO()
        runner = SnippetRunnerRemote(connection=connection)
        cond = RunningConditions(allow_import_modules=['time'])
        code = dedent("""\
        time.time()
        """)
        runner.exec(code, cond)

    def test__notallow_import_modules(self, init_instance):
        connection = DockerCommunicationIO()
        runner = SnippetRunnerRemote(connection=connection)
        cond = RunningConditions(allow_import_modules=[])
        code = dedent("""\
        time.time()
        """)
        try:
            runner.exec(code, cond)
            assert False
        except ExceptionInServerError as e:
            assert str(e) == "NameError()"



class TestDocker2:
    @pytest.fixture
    def init_instance(self):
        subprocess.run("cd docker; make", shell=True)

    def test__simple_append(self, init_instance):
        runner = SnippetRunner.run_docker()
        cond = RunningConditions()
        code = dedent("""\
        a = 1
        b = 1
        c = a+b
        """)
        runner.exec(code, cond)
    
    def test__shared_objects(self, init_instance):
        runner = SnippetRunner.run_docker()
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
    
    def test__shared_objects_error(self, init_instance):
        runner = SnippetRunner.run_docker()
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

    def test__dynamic_import(self, init_instance):
        runner = SnippetRunner.run_docker()
        cond = RunningConditions(dynamic_import=True, allow_import_modules=[])
        code = dedent("""\
        import time
        time.time()
        """)
        runner.exec(code, cond)

    def test__dynamic_import_error(self, init_instance):
        runner = SnippetRunner.run_docker()
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

    def test__allow_global_functions(self, init_instance):
        runner = SnippetRunner.run_docker()
        cond = RunningConditions(allow_global_functions=['int'])
        code = dedent("""\
        a = int(10)
        """)
        runner.exec(code, cond)

    def test__allow_global_functions_error(self, init_instance):
        runner = SnippetRunner.run_docker()
        cond = RunningConditions(allow_global_functions=['int'])
        code = dedent("""\
        a = float(10)
        """)
        try:
            runner.exec(code, cond)
            assert False
        except ExceptionInServerError as e:
            assert str(e) == "NameError()"

    def test__allow_import_modules(self, init_instance):
        runner = SnippetRunner.run_docker()
        cond = RunningConditions(allow_import_modules=['time'])
        code = dedent("""\
        time.time()
        """)
        runner.exec(code, cond)

    def test__notallow_import_modules(self, init_instance):
        runner = SnippetRunner.run_docker()
        cond = RunningConditions(allow_import_modules=[])
        code = dedent("""\
        time.time()
        """)
        try:
            runner.exec(code, cond)
            assert False
        except ExceptionInServerError as e:
            assert str(e) == "NameError()"
