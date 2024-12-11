from typing import List, Dict, Tuple, Union, Callable, Optional
from enum import Enum
from collections import defaultdict
from threading import Semaphore
import inspect
import copy
import types
import json
import bz2
import base64
import io
import uuid
import time

from .serializer import dumps, loads, SirializeFunctionCaller, UnsirializeFunctionHook
from .sync import diff, marge, apply_unsirial, SyncInstance, SyncInstanceMember, SyncSharedObject
from .exceptions import *

class ConflictSolvePolicy(Enum):
    """ConflictSolvePolicy
    """
    HOST_PRIORITIZED = 1
    CLIENT_PRIORITIZED = 2


class CommunicationInterface:
    def __init__(self):
        pass
    
    def init_share_object(self, share_object):
        return
    
    def init_configure_object(self, configure_object):
        return
    
    def start_command(self):
        pass # start thread
    
    def is_alive(self):
        return True # running or not started yet
    
    def stop(self):
        pass # stop thread

class CommunicationIO:
    def __init__(self):
        pass
    
    def send(self, data:bytearray)->int:
        pass
    
    def recv(self, delimiter:bytes=b'\n')->bytearray:
        pass
    
    def close(self):
        pass

class CommunicationLog:
    def log(self, tag, command, dump):
        pass

class Communicator:
    def __init__(self, connection:CommunicationIO, sync_frequency:float, use_compress:bool=True, log_hook:Optional[CommunicationLog]=None):
        assert sync_frequency > 0, 'sync_frequency must > 0'
        self.connection = connection
        self.sync_frequency = sync_frequency
        self.use_compress = use_compress
        self.log_hook = log_hook
        self.abort = False
    
    def _preload(self, serial_obj:dict) -> dict:
        if 'instance' in serial_obj:
            serial_obj['instance'] = {int(k):v for k,v in serial_obj['instance'].items()}
        return serial_obj        

    def _send(self, send_object) -> int:
        result = 0
        try:
            encoded_data = json.dumps(send_object)
            if self.log_hook is not None:
                self.log_hook.log('send', send_object['cmd'], encoded_data)

            if self.use_compress:
                encoded_data = encoded_data.encode('utf-8')
                compressed_buffer = io.BytesIO()
                with bz2.open(compressed_buffer, 'wb') as zipf:
                    zipf.write(encoded_data)
                compressed_buffer.seek(0)
                encoded_data = base64.b64encode(compressed_buffer.read()).decode('utf-8')
                if encoded_data.startswith("QlpoOTFBWSZTW"):
                    encoded_data = encoded_data[len("QlpoOTFBWSZTW"):]
                else:
                    encoded_data = '=' + encoded_data

            encoded_data = encoded_data.replace('\r','').replace('\n','')
            encoded_data = encoded_data + '\n'
            result = self.connection.send(encoded_data.encode('UTF-8'))
        except Exception as e:
            raise CommunicateSendError(str(e))         
        return result

    def _recv(self):
        line = self.connection.recv().decode('UTF-8')
        try:
            decoded_data = line.replace('\r','').replace('\n','')
            if self.use_compress:
                if decoded_data[0] == '=':
                    decoded_data = decoded_data[1:]
                else:
                    decoded_data = "QlpoOTFBWSZTW" + decoded_data
                decoded_data = base64.b64decode(decoded_data.encode('utf-8'))
                uncompressed_buffer = io.BytesIO(decoded_data)
                with bz2.open(uncompressed_buffer, 'rb') as zipf:
                    decoded_data = zipf.read()
            decoded_data = json.loads(decoded_data)
            if self.log_hook is not None:
                self.log_hook.log('recv', decoded_data['cmd'], line)
            return decoded_data
        except Exception as e:
            raise CommunicateRecvError(str(e)+" "+line)         

    def host(self, reciever:CommunicationInterface):
        unit_time = 1/self.sync_frequency
        tick_time = min(unit_time/100, 0.001)

        send_recv_pair = Semaphore()
        responce_data = None

        class Sender(UnsirializeFunctionHook):
            def function_call(_clz, instanceid:int, name:str, args:tuple, kwargs:dict):
                serial_data = dumps({'instanceid':instanceid, 'name':name, 'args':args, 'kwargs':kwargs}, snippet_share_only=False)
                send_responce_data = {'cmd':'responce', 'data':serial_data}
                with send_recv_pair:
                    self._send(send_responce_data)
                    return_data = self._recv()
                if type(return_data) is dict and 'cmd' in return_data:
                    if return_data['cmd'] == 'return':
                        serialized_return_data_data = return_data['data']
                        self._preload(serialized_return_data_data)
                        return loads(serialized_return_data_data)
                    elif return_data['cmd'] == 'exception':
                        if 'message' in return_data:
                            raise ExceptionInClientError(return_data['message'])
                        raise ExceptionInClientError()
                    else:
                        raise CommunicateError(f'unknown command in function result {return_data["cmd"]}')
                else:
                    raise CommunicateError()

        sender_hook = Sender()
        conflict = ConflictSolvePolicy.CLIENT_PRIORITIZED
        current_shared_object, idmap_shared_object = None, None
        current_shared_object_serial, before_shared_object_serial, client_shared_object_serial = {}, {}, {}

        with send_recv_pair:
            recieved_data = self._recv()

        while recieved_data is not None:

            start_time = time.time()

            responce_data = None

            try:
                if not reciever.is_alive():
                    responce_data = {'cmd':'end', 'result':'complete'}
                    self._send(responce_data)
                    break
                if self.abort:
                    reciever.stop()
                    responce_data = {'cmd':'end', 'result':'abort'}
                    self._send(responce_data)
                    break
            
                if type(recieved_data) is not dict and 'cmd' not in recieved_data:
                    raise CommunicateError(f'message format error')
                if recieved_data['cmd'] == 'init':
                    current_shared_object_serial = recieved_data['shared_object']
                    self._preload(current_shared_object_serial)
                    before_shared_object_serial = copy.deepcopy(current_shared_object_serial)
                    current_shared_object, idmap_shared_object = loads(current_shared_object_serial, function_hook=sender_hook, return_id_map=True)
                    reciever.init_share_object(current_shared_object)
                    responce_data = {'cmd':'init', 'data':'success'}
                elif recieved_data['cmd'] == 'start':
                    client_configure_object_serial = recieved_data['configure']
                    self._preload(client_configure_object_serial)
                    client_configure_object = loads(client_configure_object_serial)
                    conflict = ConflictSolvePolicy(int(recieved_data['conflict']))
                    reciever.init_configure_object(client_configure_object)
                    reciever.start_command()
                elif recieved_data['cmd'] == 'sync':
                    client_shared_object_serial = recieved_data['shared_object']
                    self._preload(client_shared_object_serial)
                    current_shared_object_serial = dumps(current_shared_object, snippet_share_only=False, restore_id_map=idmap_shared_object)
                    host_update = diff(before_shared_object_serial, current_shared_object_serial)
                    client_update = diff(before_shared_object_serial, client_shared_object_serial)
                    if conflict == ConflictSolvePolicy.CLIENT_PRIORITIZED:
                        diff_update = marge(client_update, host_update)
                    else:
                        diff_update = marge(host_update, client_update)
                    apply_unsirial(current_shared_object, diff_update, idmap_target_object=idmap_shared_object)
                    current_shared_object_serial = dumps(current_shared_object, snippet_share_only=False, restore_id_map=idmap_shared_object)
                    before_shared_object_serial = copy.deepcopy(current_shared_object_serial)
                    client_update = diff(client_shared_object_serial, current_shared_object_serial)
                    client_update_json = client_update.serialize()
                    responce_data = {'cmd':'update', 'data':client_update_json}
                elif recieved_data['cmd'] == 'updated':
                    responce_data = None
                elif recieved_data['cmd'] == 'echo':
                    responce_data = recieved_data
                elif recieved_data['cmd'] == 'end':
                    reciever.stop()
                    break
                elif recieved_data['cmd'] == 'exception':
                    responce_data = {'cmd':'end', 'result':'exception'}
                    break
                else:
                    raise CommunicateError(f"unknown command recieved from client - {recieved_data['cmd']}")
            except ExceptionInClientError as e:
                responce_data = {'cmd':'end', 'result':'exception', 'message':str(e)}
                break
            except Exception as e:
                responce_data = {'cmd':'exception', 'message':f'{str(type(e).__name__)}({str(e)})'}
                break

            if responce_data is None:
                current_time = time.time()
                if start_time + unit_time > current_time:
                    time.sleep((start_time + unit_time) - current_time)
        
                responce_data = {'cmd':'sync'}

            try:
                with send_recv_pair:
                    self._send(responce_data)
                    recieved_data = self._recv()
            except:
                responce_data = {'cmd':'end', 'result':'error'}
                self._send(responce_data)
                break

        try:
            if responce_data is not None:
                self._send(responce_data)
        except Exception:
            pass

        try:
            self.connection.close()
        except Exception:
            pass
       
    
    def client(self, shared_object, configure_object, conflict:ConflictSolvePolicy, snippet_share_only:bool=True, dump_object_depth:int=-1):
        exception_message = None
        exception_class = CommunicateException

        try:
            session = str(uuid.uuid4())
            responce_data = {'cmd':'echo', 'session':session}
            self._send(responce_data)
            recieved_data = self._recv()
            if type(recieved_data) is not dict and 'cmd' not in recieved_data:
                raise CommunicateError(f'message format error')
            if recieved_data['cmd'] == 'exception':
                if 'message' in recieved_data:
                    raise CommunicateInitialError(f'exception in session initial - {recieved_data["message"]}')
                raise CommunicateInitialError(f'exception in session initial')
            if not(recieved_data['cmd']  == 'echo' and recieved_data['session']  == session):
                raise CommunicateInitialError('session initial error')

            start_time = time.time()
            responce_data = {'cmd':'echo', 'start_time':int(start_time)}
            self._send(responce_data)
            recieved_data = self._recv()
            if type(recieved_data) is not dict and 'cmd' not in recieved_data:
                raise CommunicateError(f'message format error')
            if recieved_data['cmd'] == 'exception':
                if 'message' in recieved_data:
                    raise CommunicateInitialError(f'exception in echo check - {recieved_data["message"]}')
                raise CommunicateInitialError(f'exception in echo check')
            if not(recieved_data['cmd']  == 'echo' and recieved_data['start_time']  == int(start_time)):
                raise CommunicateInitialError('echo check error')

            sirial_shared_data, shared_caller = dumps(shared_object, return_caller=True, snippet_share_only=snippet_share_only, dump_object_depth=dump_object_depth)
            responce_data = {'cmd':'init', 'shared_object':sirial_shared_data}
            self._send(responce_data)
            recieved_data = self._recv()
            if type(recieved_data) is not dict and 'cmd' not in recieved_data:
                raise CommunicateError(f'message format error')
            if recieved_data['cmd'] == 'exception':
                if 'message' in recieved_data:
                    raise CommunicateInitialError(f'exception in shared_object initial - {recieved_data["message"]}')
                raise CommunicateInitialError(f'exception in shared_object initial')
            if not(recieved_data['cmd']  == 'init' and recieved_data['data']  == 'success'):
                raise CommunicateInitialError('shared_object initial error')

            configure_object_serial = dumps(configure_object, snippet_share_only=False)
            responce_data = {'cmd':'start', 'conflict':int(conflict.value), 'configure':configure_object_serial}
            self._send(responce_data)
        except Exception as e:
            raise CommunicateCannotStartError(str(e))

        while True:
            responce_data = None
            recieved_data = self._recv()
            if self.abort or recieved_data is None:
                if self.abort:
                    responce_data = {'cmd':'end', 'result':'abort'}
                else:
                    responce_data = {'cmd':'end', 'result':'error'}
                break
            else:
                try:
                    if type(recieved_data) is not dict and 'cmd' not in recieved_data:
                        raise CommunicateError(f'message format error')
                    if recieved_data['cmd'] == 'responce':
                        recieved_data_data_serial = recieved_data['data']
                        self._preload(recieved_data_data_serial)
                        function_data = loads(recieved_data_data_serial)
                        return_data = shared_caller.function_call(**function_data)
                        serialized_return_data = dumps(return_data, snippet_share_only=False)
                        responce_data = {'cmd':'return', 'data':serialized_return_data}
                    elif recieved_data['cmd'] == 'sync':
                        sirial_shared_data, shared_caller = dumps(shared_object, return_caller=True, snippet_share_only=snippet_share_only, dump_object_depth=dump_object_depth)
                        responce_data = {'cmd':'sync', 'shared_object':sirial_shared_data}
                    elif recieved_data['cmd'] == 'update':
                        diff_data_json = recieved_data['data']
                        diff_data = SyncSharedObject.unserialized(diff_data_json)
                        apply_unsirial(shared_object, diff_data)
                        responce_data = {'cmd':'updated'}
                    elif recieved_data['cmd'] == 'end':
                        responce_data = None
                        break
                    elif recieved_data['cmd'] == 'exception':
                        if 'message' in recieved_data:
                            exception_message = recieved_data['message']
                        exception_class = ExceptionInServerError
                        responce_data = {'cmd':'end', 'result':'exception'}
                        break
                    else:
                        raise CommunicateError(f'unknown command recieved from host - {recieved_data["cmd"]}')
                except Exception as e:
                    responce_data = {'cmd':'exception', 'message':f'{str(type(e).__name__)}({str(e)})'}
                    exception_message = f'{str(type(e).__name__)}({str(e)})'
                    exception_class = ExceptionInClientError
                    break
            
            if responce_data is not None:
                self._send(responce_data)

        try:
            if responce_data is not None:
                self._send(responce_data)
        except Exception as e:
            exception_message = str(e) if exception_message is None else exception_message

        try:
            self.connection.close()
        except Exception as e:
            exception_message = str(e) if exception_message is None else exception_message
        
        if exception_message is not None:
            raise exception_class(exception_message)

    def stop(self):
        self.abort = True