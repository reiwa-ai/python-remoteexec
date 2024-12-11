import pytest
from typing import List, Dict, Tuple, Union, Callable, Optional
import types
import json
import time
import queue
import threading
import remoteexec
from remoteexec.communicate import *
from remoteexec.communicate.serializer import loads, dumps
from remoteexec.communicate.sync import *
from remoteexec.communicate.exceptions import *

class QueueIO(CommunicationIO):
    def __init__(self, q1, q2):
        self.q1 = q1
        self.q2 = q2
    def send(self, data:bytearray)->int:
        self.q1.put(data)
        return len(data)
    def recv(self, delimiter:bytes=b'\n')->bytearray:
        return self.q2.get()
    def close(self):
        pass

class Reciever(CommunicationInterface):
    def __init__(self, sync_hook=None):
        self.shared_object = None
        self.sync_hook = sync_hook
    def init_share_object(self, share_object):
        self.shared_object = share_object
    def init_configure_object(self, configure_object):
        pass
    def start_command(self):
        pass
    def is_alive(self):
        if self.shared_object is not None and self.sync_hook is not None:
            self.sync_hook(self.shared_object)
        return self.shared_object is None or (\
                    (isinstance(self.shared_object,dict) and 'end' not in self.shared_object) or\
                    (not isinstance(self.shared_object,dict) and not hasattr(self.shared_object,'end')))
    def stop(self):
        pass

class TestComminucator:
    @pytest.fixture
    def init_instance(self):
        self.use_compress = False

    def make_io(self):
        qs = queue.Queue()
        qc = queue.Queue()
        fpS = QueueIO(qs, qc)
        fpC = QueueIO(qc, qs)
        return fpS, fpC
    
    def start_communicate(self, sync_frequency, reciever, shared_object, configure_object):
        fpS, fpC = self.make_io()
        server = Communicator(connection=fpS, sync_frequency=sync_frequency, use_compress=self.use_compress)
        client = Communicator(connection=fpC, sync_frequency=sync_frequency, use_compress=self.use_compress)
        def run_server():
            server.host(reciever=reciever)
        threadS = threading.Thread(target=run_server)
        threadS.start()

        def run_client():
            client.client(shared_object=shared_object, configure_object=configure_object, conflict=ConflictSolvePolicy.HOST_PRIORITIZED, snippet_share_only=False)
        threadC = threading.Thread(target=run_client)
        threadC.start()

        return threadC, threadS

    def test__sync_frequency_client2server(self, init_instance):
        shared_object = {"hoge":0}
        configure_object ={"hoge":0}
        server_history, client_history = [], []
        reciever = Reciever(lambda x:server_history.append(x["hoge"]))

        threadC, threadS = self.start_communicate(100, reciever, shared_object, configure_object)
        
        time.sleep(.5)
        client_history.append(shared_object["hoge"])
        for i in range(10):
            shared_object["hoge"] += 1
            client_history.append(shared_object["hoge"])
            time.sleep(.1)
        shared_object["end"] = 1

        threadS.join()
        threadC.join()
        assert client_history == sorted(list(set(server_history)))

    def test__sharedobject_client2server(self, init_instance):
        shared_object = {"hoge":0}
        configure_object ={"hoge":0}
        reciever = Reciever()

        threadC, threadS = self.start_communicate(5, reciever, shared_object, configure_object)
        
        time.sleep(.5)
        for i in range(10):
            shared_object["hoge"] += 1
            if i==5:
                shared_object["end"] = 1
            time.sleep(.1)

        threadS.join()
        threadC.join()
        assert shared_object == {'hoge':10,'end':1}
        assert reciever.shared_object == {'hoge':6,'end':1}
    
    def test__sharedobject_server2client(self, init_instance):
        def update(x):
            if 'stop' not in x:
                x["hoge"] += 1
        shared_object = {"hoge":0}
        configure_object ={"hoge":0}
        reciever = Reciever(update)

        threadC, threadS = self.start_communicate(100, reciever, shared_object, configure_object)
        
        time.sleep(1)
        shared_object["stop"] = 1
        time.sleep(.1) # wait to sync
        shared_object["end"] = 1
        time.sleep(.1)

        threadS.join()
        threadC.join()
        assert shared_object == reciever.shared_object
        assert shared_object['hoge'] > 0

    def test__sharedtypeinobject_client2server(self, init_instance):
        shared_object = {"hoge":[1,2,3],"hoge2":{4,5,6},"hoge3":(7,8,9),"hogehoge":{"A":0,"B":"b"}}
        configure_object = {"hoge":0}
        reciever = Reciever()

        threadC, threadS = self.start_communicate(5, reciever, shared_object, configure_object)
        
        time.sleep(.5)
        for i in range(10):
            shared_object["hoge"][0] += 1
            shared_object["hoge2"].add(i)
            shared_object["hoge3"] = (i,i**2,i**3)
            shared_object["hogehoge"]["A"] = i
            shared_object["hogehoge"]["B"] = f"_{i}"
            if i==5:
                shared_object["end"] = 1
            time.sleep(.1)

        threadS.join()
        threadC.join()
        assert shared_object["hoge"] == [11,2,3]
        assert shared_object["hoge2"] == {0,1,2,3,4,5,6,7,8,9}
        assert shared_object["hoge3"] == (9,81,729)
        assert shared_object["hogehoge"] == {"A":9,"B":"_9"}
        assert reciever.shared_object["hoge"] == [7,2,3]
        assert reciever.shared_object["hoge2"] == {0,1,2,3,4,5,6}
        assert reciever.shared_object["hoge3"] == (5,25,125)
        assert reciever.shared_object["hogehoge"] == {"A":5,"B":"_5"}
    
    def test__sharedtypeinobject_server2client(self, init_instance):
        def update(x):
            if 'stop' not in x:
                i = x["hoge"][0]
                x["hoge"][0] += 1
                x["hoge2"].add(i)
                x["hoge3"] = (i,i**2,i**3)
                x["hogehoge"]["A"] = i
                x["hogehoge"]["B"] = f"_{i}"
        shared_object = {"hoge":[1,2,3],"hoge2":{4,5,6},"hoge3":(7,8,9),"hogehoge":{"A":0,"B":"b"}}
        configure_object ={"hoge":0}
        reciever = Reciever(update)

        threadC, threadS = self.start_communicate(100, reciever, shared_object, configure_object)
        
        time.sleep(1)
        shared_object["stop"] = 1
        time.sleep(.1) # wait to sync
        shared_object["end"] = 1
        time.sleep(.1)

        threadS.join()
        threadC.join()
        assert shared_object == reciever.shared_object
        assert shared_object['hoge'][0] > 1

    def test__sharedclass_client2server(self, init_instance):
        class shared:
            def __init__(self):
                self.hoge = 0
        shared_object = shared()
        configure_object = shared()
        reciever = Reciever()

        threadC, threadS = self.start_communicate(100, reciever, shared_object, configure_object)
        
        time.sleep(.5)
        for i in range(10):
            shared_object.hoge += 1
            if i==5:
                shared_object.end = 1
            time.sleep(.1)

        threadS.join()
        threadC.join()
        assert shared_object.hoge == 10 and shared_object.end == 1
        assert reciever.shared_object.hoge == 6 and reciever.shared_object.end == 1

    def test__sharedclass_server2client(self, init_instance):
        def update(x):
            if not hasattr(x, 'stop'):
                x.hoge += 1
        class shared:
            def __init__(self):
                self.hoge = 0
        shared_object = shared()
        configure_object = shared()
        reciever = Reciever(update)

        threadC, threadS = self.start_communicate(100, reciever, shared_object, configure_object)
        
        time.sleep(1)
        shared_object.stop = 1
        time.sleep(.1) # wait to sync
        shared_object.end = 1
        time.sleep(.1)

        threadS.join()
        threadC.join()
        assert shared_object.hoge == reciever.shared_object.hoge

    def test__function_server2client(self, init_instance):
        history = []
        def update(x):
            if not hasattr(x, 'stop'):
                x.hoge += 1
                x.buufuu()
        class shared:
            def __init__(self):
                self.hoge = 0
            def buufuu(self):
                history.append(1)
        shared_object = shared()
        configure_object = shared()
        reciever = Reciever(update)

        threadC, threadS = self.start_communicate(100, reciever, shared_object, configure_object)
        
        time.sleep(1)
        shared_object.stop = 1
        time.sleep(.1) # wait to sync
        shared_object.end = 1
        time.sleep(.1)

        threadS.join()
        threadC.join()
        assert shared_object.hoge == reciever.shared_object.hoge
        assert shared_object.hoge == len(history)

    def test__functionargs_server2client(self, init_instance):
        history = []
        def update(x):
            if not hasattr(x, 'stop'):
                x.hoge += 1
                x.buufuu(x.hoge, x.hoge**2)
        class shared:
            def __init__(self):
                self.hoge = 0
            def buufuu(self, x, y):
                history.append((x,y))
        shared_object = shared()
        configure_object = shared()
        reciever = Reciever(update)

        threadC, threadS = self.start_communicate(100, reciever, shared_object, configure_object)
        
        time.sleep(1)
        shared_object.stop = 1
        time.sleep(.1) # wait to sync
        shared_object.end = 1
        time.sleep(.1)

        threadS.join()
        threadC.join()
        assert shared_object.hoge == reciever.shared_object.hoge
        assert shared_object.hoge == len(history)
        assert history[:4] == [(1,1),(2,4),(3,9),(4,16)]

    def test__functionkwargs_server2client(self, init_instance):
        history = []
        def update(x):
            if not hasattr(x, 'stop'):
                x.hoge += 1
                x.buufuu(y=x.hoge, x=x.hoge**2)
        class shared:
            def __init__(self):
                self.hoge = 0
            def buufuu(self, x, y):
                history.append((x,y))
        shared_object = shared()
        configure_object = shared()
        reciever = Reciever(update)

        threadC, threadS = self.start_communicate(100, reciever, shared_object, configure_object)
        
        time.sleep(1)
        shared_object.stop = 1
        time.sleep(.1) # wait to sync
        shared_object.end = 1
        time.sleep(.1)

        threadS.join()
        threadC.join()
        assert shared_object.hoge == reciever.shared_object.hoge
        assert shared_object.hoge == len(history)
        assert history[:4] == [(1,1),(4,2),(9,3),(16,4)]

    def test__functionargskwargs_server2client(self, init_instance):
        history = []
        def update(x):
            if not hasattr(x, 'stop'):
                x.hoge += 1
                x.buufuu(x.hoge, y=x.hoge**2)
        class shared:
            def __init__(self):
                self.hoge = 0
            def buufuu(self, x, y):
                history.append((x,y))
        shared_object = shared()
        configure_object = shared()
        reciever = Reciever(update)

        threadC, threadS = self.start_communicate(100, reciever, shared_object, configure_object)
        
        time.sleep(1)
        shared_object.stop = 1
        time.sleep(.1) # wait to sync
        shared_object.end = 1
        time.sleep(.1)

        threadS.join()
        threadC.join()
        assert shared_object.hoge == reciever.shared_object.hoge
        assert shared_object.hoge == len(history)
        assert history[:4] == [(1,1),(2,4),(3,9),(4,16)]

    def test__functionreturn_server2client(self, init_instance):
        def update(x):
            if not hasattr(x, 'stop'):
                x.hoge += 1
                x.history.append(x.buufuu(x.hoge, y=x.hoge**2))
        class shared:
            def __init__(self):
                self.hoge = 0
                self.history = []
            def buufuu(self, x, y):
                return x + y**2
        shared_object = shared()
        configure_object = shared()
        reciever = Reciever(update)

        threadC, threadS = self.start_communicate(100, reciever, shared_object, configure_object)
        
        time.sleep(1)
        shared_object.stop = 1
        time.sleep(.1) # wait to sync
        shared_object.end = 1
        time.sleep(.1)

        threadS.join()
        threadC.join()
        assert shared_object.hoge == reciever.shared_object.hoge
        assert shared_object.history[:4] == [2,18,84,260]

    def test__functionreturnobject_server2client(self, init_instance):
        def update(x):
            if not hasattr(x, 'stop'):
                x.hoge += 1
                x.history.append(x.buufuu(x.hoge, y=x.hoge**2))
        class shared:
            def __init__(self):
                self.hoge = 0
                self.history = []
            def buufuu(self, x, y):
                return (x, y**2)
        shared_object = shared()
        configure_object = shared()
        reciever = Reciever(update)

        threadC, threadS = self.start_communicate(100, reciever, shared_object, configure_object)
        
        time.sleep(1)
        shared_object.stop = 1
        time.sleep(.1) # wait to sync
        shared_object.end = 1
        time.sleep(.1)

        threadS.join()
        threadC.join()
        assert shared_object.hoge == reciever.shared_object.hoge
        assert shared_object.history[:4] == [(1,1),(2,16),(3,81),(4,256)]

    def test__exception_errorinserver(self, init_instance):
        def update(x):
            if not hasattr(x, 'stop'):
                x.hoge -= 1
                x.history.append(x.buufuu(x.hoge, y=1/x.hoge))
        class shared:
            def __init__(self):
                self.hoge = 5
                self.history = []
            def buufuu(self, x, y):
                return x + y
        shared_object = shared()
        configure_object = shared()
        reciever = Reciever(update)

        fpS, fpC = self.make_io()
        server = Communicator(connection=fpS, sync_frequency=100, use_compress=self.use_compress)
        client = Communicator(connection=fpC, sync_frequency=100, use_compress=self.use_compress)
        def run_server():
            server.host(reciever=reciever)
        threadS = threading.Thread(target=run_server)
        threadS.start()

        error_handled = False
        error_message = ""

        def run_client():
            nonlocal error_handled, error_message
            try:
                client.client(shared_object=shared_object, configure_object=configure_object, conflict=ConflictSolvePolicy.HOST_PRIORITIZED, snippet_share_only=False)
                assert False
            except ExceptionInServerError as e:
                error_handled = True
                error_message = str(e)
        threadC = threading.Thread(target=run_client)
        threadC.start()
        
        time.sleep(1)
        assert not (threadC.is_alive() or threadS.is_alive())
        
        shared_object.stop = 1
        time.sleep(.1) # wait to sync
        shared_object.end = 1
        time.sleep(.1)

        threadS.join()
        threadC.join()

        assert error_handled
        assert error_message == "ZeroDivisionError(division by zero)"
        
    def test__exception_errorinclient(self, init_instance):
        def update(x):
            if not hasattr(x, 'stop'):
                x.hoge -= 1
                x.history.append(x.buufuu(x.hoge, y=x.hoge))
        class shared:
            def __init__(self):
                self.hoge = 5
                self.history = []
            def buufuu(self, x, y):
                return (x+1) / y
        shared_object = shared()
        configure_object = shared()
        reciever = Reciever(update)

        fpS, fpC = self.make_io()
        server = Communicator(connection=fpS, sync_frequency=100, use_compress=self.use_compress)
        client = Communicator(connection=fpC, sync_frequency=100, use_compress=self.use_compress)
        def run_server():
            server.host(reciever=reciever)
        threadS = threading.Thread(target=run_server)
        threadS.start()

        error_handled = False
        error_message = ""

        def run_client():
            nonlocal error_handled, error_message
            try:
                client.client(shared_object=shared_object, configure_object=configure_object, conflict=ConflictSolvePolicy.HOST_PRIORITIZED, snippet_share_only=False)
                assert False
            except ExceptionInClientError as e:
                error_handled = True
                error_message = str(e)
        threadC = threading.Thread(target=run_client)
        threadC.start()
        
        time.sleep(1)
        assert not (threadC.is_alive() or threadS.is_alive())
        
        shared_object.stop = 1
        time.sleep(.1) # wait to sync
        shared_object.end = 1
        time.sleep(.1)

        threadS.join()
        threadC.join()

        assert error_handled
        assert error_message == "ZeroDivisionError(division by zero)"
        
