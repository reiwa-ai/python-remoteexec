from typing import List, Dict, Tuple, Union, Callable, Optional
from enum import Enum
from collections import defaultdict
import inspect
import types
import json
import zipfile
import base64
import io

from .exceptions import *

__snippet_share__ = set()

def snippet_share(obj):
    __snippet_share__.add(obj)
    return obj

class SiriarizeInstance:
    def __init__(self, obj:object, objdict:Dict[str,object], names:Tuple[str], funcs:Optional[Tuple[str]]=None):
        self.obj = obj
        self.objdict = objdict
        self.names = names
        self.funcs = funcs if funcs else tuple()

class SiriarizeDictInstance:
    def __init__(self, obj:object, objdict:Dict[object,object]):
        self.obj = obj
        self.objdict = objdict


class SirializeFunctionCaller:
    def __init__(self, out_instance):
        if out_instance is None or type(out_instance) is not dict:
            raise SirializedFunctionError
        self.out_instance = out_instance
    
    def function_call(self, instanceid:int, name:str, args:tuple, kwargs:dict):
        if instanceid not in self.out_instance:
            raise SirializedFunctionError
        if type(self.out_instance[instanceid]) is not SiriarizeInstance:
            raise SirializedFunctionError
        if name not in self.out_instance[instanceid].funcs:
            raise SirializedFunctionError
        func = self.out_instance[instanceid].obj.__getattribute__(name)
        return func(*args, **kwargs)


def dumps(share_object:object,
          return_caller:bool=False,
          snippet_share_only:bool=True,
          dump_object_depth:int=-1,
          restore_id_map:Optional[dict]=None) -> Union[Dict[str,object],Tuple[Dict[str,object], SirializeFunctionCaller]]:

    out_instance = {}
    type_typename = {int:'int',float:'float',str:'str',bool:'bool',list:'list',set:'set',tuple:'tuple',dict:'dict'}

    def _id(obj):
        if obj.__class__.__name__.startswith('__serial_id_'):
            return int(obj.__class__.__name__[len('__serial_id_'):])
        elif restore_id_map is not None and id(obj) in restore_id_map:
            return int(restore_id_map[id(obj)])
        return id(obj)

    def _list(obj, depth):
        d, e, f = None, None, None
        if _id(obj) not in out_instance:
            if obj is None or type(obj) is int or type(obj) is float or type(obj) is str is float or type(obj) is bool:
                pass
            elif isinstance(obj, list) or isinstance(obj, tuple) or isinstance(obj, set):
                d = {str(key):value for key,value in enumerate(obj)}
            elif isinstance(obj, dict):
                d = None
                e = obj
            elif hasattr(obj, '__dict__'):
                if snippet_share_only==False or type(obj) in __snippet_share__:
                    d = {key:value for key,value in inspect.getmembers(obj) 
                            if not key.startswith('__')
                            and not inspect.isabstract(value)
                            and not inspect.isbuiltin(value)
                            and not inspect.isfunction(value)
                            and not inspect.isgenerator(value)
                            and not inspect.isgeneratorfunction(value)
                            and not inspect.ismethod(value)
                            and not inspect.ismethoddescriptor(value)
                            and not inspect.isroutine(value)}
                    f = tuple(key for key,value in inspect.getmembers(obj) 
                            if not key.startswith('__')
                            and (inspect.ismethod(value) or inspect.isfunction(value)))
            if dump_object_depth < 0 or dump_object_depth > depth:
                if d is not None:
                    out_instance[_id(obj)] = SiriarizeInstance(obj, d, tuple(d.keys()), f)
                    for value in d.values():
                        _list(obj=value, depth=depth+1)
                elif e is not None:
                    out_instance[_id(obj)] = SiriarizeDictInstance(obj, e)
                    for key,value in e.items():
                        _list(obj=key, depth=depth+1) # to tuple key
                        _list(obj=value, depth=depth+1)

    _list(obj=share_object, depth=0)

    seriarized_instance = {}
    for objid, instance in out_instance.items():
        if type(instance) is SiriarizeDictInstance:
            seriarized_instance[objid] = {}
            seriarized_instance[objid]['__type__'] = 'dict'
            seriarized_instance[objid]['keys'] = []
            seriarized_instance[objid]['values'] = []
            for k,v in instance.obj.items():
                if k is None or type(k) is int or type(k) is float or type(k) is str or type(k) is bool:
                    seriarized_instance[objid]['keys'].append({'type':'native','value':k})
                else:
                    seriarized_instance[objid]['keys'].append({'type':'pointer','value':_id(k)})
                if v is None or type(v) is int or type(v) is float or type(v) is str or type(v) is bool:
                    seriarized_instance[objid]['values'].append({'type':'native','value':v})
                else:
                    seriarized_instance[objid]['values'].append({'type':'pointer','value':_id(v)})
        else:
            seriarized_instance[objid] = {}
            if instance.obj is None:
                seriarized_instance[objid]['__type__'] = 'None'
            elif type(instance.obj) in type_typename:
                seriarized_instance[objid]['__type__'] = type_typename[type(instance.obj)]
            else:
                seriarized_instance[objid]['__type__'] = 'object'
            
            for name in instance.names:
                if type(instance.obj) is list or type(instance.obj) is tuple or type(instance.obj) is set:
                    obj = instance.objdict[name]
                elif type(instance.obj) is dict:
                    obj = instance.objdict[name]
                else:
                    obj = instance.obj.__getattribute__(name)
                if obj is None or type(obj) is int or type(obj) is float or type(obj) is str or type(obj) is bool:
                    seriarized_instance[objid][name] = {'type':'native','value':obj}
                elif _id(obj) in out_instance:
                    seriarized_instance[objid][name] = {'type':'pointer','value':_id(obj)}
            for func in instance.funcs:
                seriarized_instance[objid][func] = {'type':'function'}
        
    if share_object is None or type(share_object) is int or type(share_object) is float or type(share_object) is str or type(share_object) is bool:
        data = {'object':0,'value':share_object}
    elif _id(share_object) in seriarized_instance:
        data = {'object':_id(share_object),'instance':seriarized_instance}
    else:
        raise SirializeError()

    if return_caller:
        return data, SirializeFunctionCaller(out_instance)
    else:
        return data


class UnsirializeFunctionHook:
    def function_call(self, instanceid:int, name:str, args:tuple, kwargs:dict):
        return None


def loads(decoded_data:Dict[str,object], function_hook:Optional[UnsirializeFunctionHook]=None, return_id_map:bool=False) -> object:
    class sparselistbase(list):
        def __setitem__(self, indexstr, value):
            index = int(indexstr)
            missing = index - len(self) + 1
            if missing > 0:
                self.extend([None] * missing)
            super().__setitem__(index, value)
        def __getitem__(self, index):
            try: return super().__getitem__(index)
            except IndexError: return None
        def __str__(self):
            return str(super(list))
    class sparselist(sparselistbase):
        pass
    class sparseset(sparselistbase):
        pass
    class sparsetuple(sparselistbase):
        pass
    class sparsedict(defaultdict):
        def __init__(self):
            super().__init__(lambda:None)
        def __str__(self):
            return str({k:v for k,v in self.items()})
    class sparseobject(object):
        def __init__(self):
            self.__updated__ = False

    typename_type = {'int':int,'float':float,'str':str,'bool':bool,'list':sparselist,'set':sparseset,'tuple':sparsetuple,'dict':sparsedict}

    if type(decoded_data) is not dict or 'object' not in decoded_data:
        raise UnsirializeError()
    
    if decoded_data['object']==0 and 'value' in decoded_data:
        if return_id_map:
            return decoded_data['value'], {}
        return decoded_data['value']

    if 'instance' not in decoded_data:
        raise UnsirializeError()
    
    rootid = decoded_data['object']
    instance = decoded_data['instance']

    if type(instance) is not dict:
        raise UnsirializeError()
    
    unsirialized_instance = {}

    if rootid not in instance:
        raise UnsirializeError()
    
    for instanceid, instancevalue in instance.items():
        if type(instancevalue) is not dict:
            raise UnsirializeError()
        if '__type__' not in instancevalue:
            raise UnsirializeError()
        if instancevalue['__type__'] in typename_type:
            clz = types.new_class(f'__serial_id_{instanceid}', (typename_type[instancevalue['__type__']],))
        else:
            clz = types.new_class(f'__serial_id_{instanceid}', (sparseobject,))
        unsirialized_instance[instanceid] = clz()

    for instanceid, instancevalue in instance.items():
        if instancevalue['__type__'] in 'dict':
            kvgenerator = zip(instancevalue['keys'], instancevalue['values'])
        else:
            kvgenerator = instancevalue.items()
        for _name, value in kvgenerator:
            if type(_name) is dict:
                if 'type' not in _name:
                    raise UnsirializeError()
                if _name['type'] == 'native':
                    if 'value' not in _name:
                        raise UnsirializeError()
                    name = _name['value']
                elif _name['type'] == 'pointer':
                    if 'value' not in _name or _name['value'] not in unsirialized_instance:
                        raise UnsirializeError()
                    name = unsirialized_instance[_name['value']]
                else:
                    raise UnsirializeError()
            elif not _name.startswith('__'):
                name = _name
            else:
                name = None
            if name is not None:
                if type(value) is not dict  or 'type' not in value:
                    raise UnsirializeError()
                if value['type'] == 'native':
                    if 'value' not in value:
                        raise UnsirializeError()
                    if hasattr(unsirialized_instance[instanceid], '__setitem__'):
                        unsirialized_instance[instanceid][name] = value['value']
                    else:
                        unsirialized_instance[instanceid].__setattr__(name,value['value'])
                elif value['type'] == 'pointer':
                    if 'value' not in value or value['value'] not in unsirialized_instance:
                        raise UnsirializeError()
                    if hasattr(unsirialized_instance[instanceid], '__setitem__'):
                        unsirialized_instance[instanceid][name] = unsirialized_instance[value['value']]
                    else:
                        unsirialized_instance[instanceid].__setattr__(name,unsirialized_instance[value['value']])
                elif value['type'] == 'function':
                    def _apply_function_hook(_instanceid, _name): # new namespace
                        if function_hook is not None:
                            unsirialized_instance[_instanceid].__setattr__(_name, lambda *args, **kwargs: function_hook.function_call(_instanceid, _name, args, kwargs))
                        else:
                            unsirialized_instance[_instanceid].__setattr__(_name, lambda *args, **kwargs: None)
                    _apply_function_hook(instanceid, name)
                else:
                    raise UnsirializeError()
        
    if rootid not in unsirialized_instance:
        raise UnsirializeError()

    result_id_map = {}
    
    def reverce_types(obj):
        if isinstance(obj, sparselist):
            res = [reverce_types(l) for l in obj]
            result_id_map[id(res)] = int(obj.__class__.__name__[len('__serial_id_'):])
            return res
        elif isinstance(obj, sparseset):
            res = {reverce_types(l) for l in obj}
            result_id_map[id(res)] = int(obj.__class__.__name__[len('__serial_id_'):])
            return res
        elif isinstance(obj, sparsetuple):
            res = tuple(reverce_types(l) for l in obj)
            result_id_map[id(res)] = int(obj.__class__.__name__[len('__serial_id_'):])
            return res
        elif isinstance(obj, sparsedict):
            res = {reverce_types(k):reverce_types(v) for k,v in obj.items()}
            result_id_map[id(res)] = int(obj.__class__.__name__[len('__serial_id_'):])
            return res
        elif type(obj) is int or type(obj) is float or type(obj) is str or type(obj) is bool:
            result_id_map[id(obj)] = id(obj)
            return obj
        elif hasattr(obj, '__updated__'):
            delattr(obj, '__updated__')
            for key,value in inspect.getmembers(obj):
                if not key.startswith('__'):
                    obj.__setattr__(key,reverce_types(value))
            result_id_map[id(obj)] = int(obj.__class__.__name__[len('__serial_id_'):])
            return obj
        else:
            result_id_map[id(obj)] = id(obj)
            return obj
    data = reverce_types(unsirialized_instance[rootid])

    if return_id_map:
        return data, result_id_map

    return data


