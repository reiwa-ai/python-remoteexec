import pytest
from typing import List, Dict, Tuple, Union, Callable, Optional
import types
import json
import time
import remoteexec
from remoteexec.communicate import *
from remoteexec.communicate.serializer import loads, dumps


class TestSerializerLoads:
    @pytest.fixture
    def init_instance(self):
        pass

    def test__single_load(self, init_instance):
        clz = types.new_class(f'test__serialize_dump_1', (object,))
        c = clz()
        c.__setattr__('hogehoge','value1')
        d = dumps(c, snippet_share_only=False)
        e = loads(d)
        assert e.hogehoge == 'value1'

    def test__native_load(self, init_instance):
        d = dumps(123, snippet_share_only=False)
        e = loads(d)
        assert e==123
        d = dumps(123.456, snippet_share_only=False)
        e = loads(d)
        assert e==123.456
        d = dumps('789', snippet_share_only=False)
        e = loads(d)
        assert e=='789'
        d = dumps(None, snippet_share_only=False)
        e = loads(d)
        assert e==None
        d = dumps(True, snippet_share_only=False)
        e = loads(d)
        assert e==True

    def test__tupleintype_load(self, init_instance):
        d = dumps([(1,2,3),(4,5,6)], snippet_share_only=False)
        e = loads(d)
        assert e[0]==(1,2,3)
        assert e[1]==(4,5,6)
        d = dumps({(1,2,3),(4,5,6)}, snippet_share_only=False)
        e = loads(d)
        assert e=={(1,2,3),(4,5,6)}
        d = dumps(((1,2,3),(4,5,6)), snippet_share_only=False)
        e = loads(d)
        assert e[0]==(1,2,3)
        assert e[1]==(4,5,6)
        d = dumps({'A':(1,2,3),'B':(4,5,6)}, snippet_share_only=False)
        e = loads(d)
        assert e['A']==(1,2,3)
        assert e['B']==(4,5,6)

    def test__singlehierarchy_load(self, init_instance):
        clz1 = types.new_class(f'test__serialize_dump_1', (object,))
        clz2 = types.new_class(f'test__serialize_dump_2', (object,))
        clz3 = types.new_class(f'test__serialize_dump_3', (object,))
        c1 = clz1()
        c2 = clz2()
        c3 = clz3()
        c1.__setattr__('hogehoge1','value1')
        c1.__setattr__('hierarchy1',c2)
        c2.__setattr__('hogehoge2','value2')
        c2.__setattr__('hierarchy2',c3)
        c3.__setattr__('hogehoge3','value3')
        d = dumps(c1, snippet_share_only=False)
        e = loads(d)
        assert e.hogehoge1 == 'value1'
        assert e.hierarchy1.hogehoge2 == 'value2'
        assert e.hierarchy1.hierarchy2.hogehoge3 == 'value3'

    def test__singlecirculation_load(self, init_instance):
        clz1 = types.new_class(f'test__serialize_dump_1', (object,))
        clz2 = types.new_class(f'test__serialize_dump_2', (object,))
        clz3 = types.new_class(f'test__serialize_dump_3', (object,))
        c1 = clz1()
        c2 = clz2()
        c3 = clz3()
        c1.__setattr__('hogehoge1','value1')
        c1.__setattr__('hierarchy1',c2)
        c2.__setattr__('hogehoge2','value2')
        c2.__setattr__('hierarchy2',c3)
        c3.__setattr__('hogehoge3','value3')
        c3.__setattr__('hierarchy3',c1)
        d = dumps(c1, snippet_share_only=False)
        e = loads(d)
        assert e.hogehoge1 == 'value1'
        assert e.hierarchy1.hogehoge2 == 'value2'
        assert e.hierarchy1.hierarchy2.hogehoge3 == 'value3'
        assert e.hierarchy1.hierarchy2.hierarchy3 == e

    def test__types_load(self, init_instance):
        clz = types.new_class(f'test__serialize_dump_1', (object,))
        c = clz()
        c.__setattr__('hogehogestr','value1')
        c.__setattr__('hogehogeint',1)
        c.__setattr__('hogehogefloat',2.001)
        c.__setattr__('hogehogedict',{'a':0,'b':'B'})
        c.__setattr__('hogehogelist',[1,2,3])
        c.__setattr__('hogehogeset',{4,5,6})
        c.__setattr__('hogehogetuple',(7,8,9))
        d = dumps(c, snippet_share_only=False)
        e = loads(d)
        assert e.hogehogestr == 'value1'
        assert e.hogehogeint == 1
        assert e.hogehogefloat == 2.001
        assert e.hogehogedict == {'a':0,'b':'B'}
        assert e.hogehogelist == [1,2,3]
        assert e.hogehogeset == {4,5,6}
        assert e.hogehogetuple == (7,8,9)
        assert type(e.hogehogedict) is dict
        assert type(e.hogehogelist) is list
        assert type(e.hogehogeset) is set
        assert type(e.hogehogetuple) is tuple

    def test__class_load(self, init_instance):
        class clz1:
            def __init__(self, c):
                self.c = c
        class clz2:
            def __init__(self, c):
                self.c = c
                self.hoge = 'hoge'
        c2 = clz2(10)
        c1 = clz1(c2)
        d = dumps(c1, snippet_share_only=False)
        e = loads(d)
        assert e.c.c == 10
        assert e.c.hoge == 'hoge'

    def test__classcirculation_load(self, init_instance):
        class clz1:
            def __init__(self, c):
                self.c = c
        class clz2:
            def __init__(self, c):
                self.c = c
                self.hoge = 'hoge'
        c2 = clz2(10)
        c1 = clz1(c2)
        c2.c = c1
        d = dumps(c1, snippet_share_only=False)
        e = loads(d)
        assert e.c == e.c.c.c
        assert e.c.c == e.c.c.c.c
        assert e.c.hoge == 'hoge'

    def test__dicthierarchy_load(self, init_instance):
        c1 = {}
        c2 = {}
        c3 = {}
        c1['hogehoge1'] = 'value1'
        c1['hierarchy1'] = c2
        c2['hogehoge2'] = 'value2'
        c2['hierarchy2'] = c3
        c3['hogehoge3'] = 'value3'
        d = dumps(c1, snippet_share_only=False)
        e = loads(d)
        assert e['hogehoge1'] == 'value1'
        assert e['hierarchy1']['hogehoge2'] == 'value2'
        assert e['hierarchy1']['hierarchy2']['hogehoge3'] == 'value3'

    def test__listhierarchy_load(self, init_instance):
        c1 = []
        c2 = []
        c3 = []
        c1.append('value1')
        c1.append(c2)
        c2.append('value2')
        c2.append(c3)
        c3.append('value3')
        d = dumps(c1, snippet_share_only=False)
        e = loads(d)
        assert e[0] == 'value1'
        assert e[1][0] == 'value2'
        assert e[1][1][0] == 'value3'

    def test__tuplehierarchy_load(self, init_instance):
        c = {'hogehoge1':'value1','hierarchy1':('value2',('value3',0))}
        d = dumps(c, snippet_share_only=False)
        e = loads(d)
        assert e['hogehoge1'] == 'value1'
        assert e['hierarchy1'][0] == 'value2'
        assert e['hierarchy1'][1][0] == 'value3'
        assert e['hierarchy1'][1][1] == 0

    def test__reconstract_ids(self, init_instance):
        clz = types.new_class(f'test__serialize_dump_1', (object,))
        c = clz()
        c.__setattr__('hogehoge','value1')
        d = dumps(c, snippet_share_only=False)
        assert d['object']==id(c)
        e, restore_id_map = loads(d, return_id_map=True)
        assert e.hogehoge == 'value1'
        f = dumps(e, snippet_share_only=False, restore_id_map=restore_id_map)
        assert f=={'object': id(c), 'instance': 
                    {id(c): {'__type__': 'object', 'hogehoge': {'type': 'native', 'value': 'value1'}}}}

    def test__reconstract_class_ids(self, init_instance):
        class clz1:
            def __init__(self, c):
                self.c = c
        class clz2:
            def __init__(self, c):
                self.c = c
                self.hoge = 'hoge'
        c2 = clz2(10)
        c1 = clz1(c2)
        d = dumps(c1, snippet_share_only=False)
        assert d['object']==id(c1)
        assert d['instance'][id(c1)]['c']['value']==id(c2)
        e, restore_id_map = loads(d, return_id_map=True)
        assert e.c.c == 10
        assert e.c.hoge == 'hoge'
        f = dumps(e, snippet_share_only=False, restore_id_map=restore_id_map)
        assert f=={'object': id(c1), 'instance': {
                    id(c1): {'__type__': 'object', 'c': {'type': 'pointer', 'value': id(c2)}},
                    id(c2): {'__type__': 'object', 'c': {'type': 'native', 'value': 10}, 'hoge': {'type': 'native', 'value': 'hoge'}}}}

    def test__reconstract_types_ids(self, init_instance):
        clz = types.new_class(f'test__serialize_dump_1', (object,))
        c = clz()
        c.__setattr__('hogehogestr','value1')
        c.__setattr__('hogehogeint',1)
        c.__setattr__('hogehogefloat',2.001)
        c.__setattr__('hogehogedict',{'a':0,'b':'B'})
        c.__setattr__('hogehogelist',[1,2,3])
        c.__setattr__('hogehogeset',{4,5,6})
        c.__setattr__('hogehogetuple',(7,8,9))
        d = dumps(c, snippet_share_only=False)
        e, restore_id_map = loads(d, return_id_map=True)
        assert e.hogehogestr == 'value1'
        assert e.hogehogeint == 1
        assert e.hogehogefloat == 2.001
        assert e.hogehogedict == {'a':0,'b':'B'}
        assert e.hogehogelist == [1,2,3]
        assert e.hogehogeset == {4,5,6}
        assert e.hogehogetuple == (7,8,9)
        assert type(e.hogehogedict) is dict
        assert type(e.hogehogelist) is list
        assert type(e.hogehogeset) is set
        assert type(e.hogehogetuple) is tuple
        f = dumps(e, snippet_share_only=False, restore_id_map=restore_id_map)
        assert f=={'object': id(c), 'instance': {
                    id(c): {'__type__': 'object', 'hogehogestr': {'type': 'native', 'value': 'value1'}, 
                                                  'hogehogeint': {'type': 'native', 'value': 1},
                                                  'hogehogefloat': {'type': 'native', 'value': 2.001}, 
                                                  'hogehogedict': {'type': 'pointer', 'value': id(c.hogehogedict)},
                                                  'hogehogelist': {'type': 'pointer', 'value': id(c.hogehogelist)}, 
                                                  'hogehogeset': {'type': 'pointer', 'value': id(c.hogehogeset)},
                                                  'hogehogetuple': {'type': 'pointer', 'value': id(c.hogehogetuple)}},
                    id(c.hogehogedict): {'__type__': 'dict', 'keys': [{'type': 'native', 'value': 'a'}, {'type': 'native', 'value': 'b'}], 'values': [{'type': 'native', 'value': 0}, {'type': 'native', 'value': 'B'}]},
                    id(c.hogehogelist): {'__type__': 'list', '0': {'type': 'native', 'value': 1}, '1': {'type': 'native', 'value': 2}, '2': {'type': 'native', 'value': 3}},
                    id(c.hogehogeset): {'__type__': 'set', '0': {'type': 'native', 'value': 4}, '1': {'type': 'native', 'value': 5}, '2': {'type': 'native', 'value': 6}},
                    id(c.hogehogetuple): {'__type__': 'tuple', '0': {'type': 'native', 'value': 7}, '1': {'type': 'native', 'value': 8}, '2': {'type': 'native', 'value': 9}}}}

    def test__simple_function_hook(self, init_instance):
        check = False
        def f():
            nonlocal check
            check = True
        clz = types.new_class(f'test__serialize_dump_1', (object,))
        c = clz()
        c.__setattr__('hogehoge',f)
        d, caller = dumps(c, snippet_share_only=False, return_caller=True)

        class hookClz(UnsirializeFunctionHook):
            def function_call(_clz, instanceid:int, name:str, args:tuple, kwargs:dict):
                return caller.function_call(instanceid, name, args, kwargs)
        
        hook = hookClz()
        e = loads(d, function_hook=hook)
        e.hogehoge()
        assert check

    def test__class_function_hook(self, init_instance):
        check = []
        class clz:
            def hogehoge(self):
                check.append('checked')
        c = clz()
        d, caller = dumps(c, snippet_share_only=False, return_caller=True)

        class hookClz(UnsirializeFunctionHook):
            def function_call(_clz, instanceid:int, name:str, args:tuple, kwargs:dict):
                return caller.function_call(instanceid, name, args, kwargs)
        
        hook = hookClz()
        e = loads(d, function_hook=hook)
        e.hogehoge()
        assert check==['checked']

    def test__simpleargs_function_hook(self, init_instance):
        check = False
        def f(a,b,c):
            nonlocal check
            if a==1 and b==10 and c==100:
                check = True
        clz = types.new_class(f'test__serialize_dump_1', (object,))
        c = clz()
        c.__setattr__('hogehoge',f)
        d, caller = dumps(c, snippet_share_only=False, return_caller=True)

        class hook(UnsirializeFunctionHook):
            def function_call(instanceid:int, name:str, args:tuple, kwargs:dict):
                return caller.function_call(instanceid, name, args, kwargs)
        
        e = loads(d, function_hook=hook)
        e.hogehoge(1,10,100)
        assert check

    def test__classargs_function_hook(self, init_instance):
        check = []
        class clz:
            def hogehoge(self,a,b,c):
                if a==1 and b==10 and c==100:
                    check.append('checked')
        c = clz()
        d, caller = dumps(c, snippet_share_only=False, return_caller=True)

        class hook(UnsirializeFunctionHook):
            def function_call(instanceid:int, name:str, args:tuple, kwargs:dict):
                return caller.function_call(instanceid, name, args, kwargs)
        
        e = loads(d, function_hook=hook)
        e.hogehoge(1,10,100)
        assert check==['checked']

    def test__simplekwargs_function_hook(self, init_instance):
        check = False
        def f(a,b,c):
            nonlocal check
            if a==1 and b==10 and c==100:
                check = True
        clz = types.new_class(f'test__serialize_dump_1', (object,))
        c = clz()
        c.__setattr__('hogehoge',f)
        d, caller = dumps(c, snippet_share_only=False, return_caller=True)

        class hook(UnsirializeFunctionHook):
            def function_call(instanceid:int, name:str, args:tuple, kwargs:dict):
                return caller.function_call(instanceid, name, args, kwargs)
        
        e = loads(d, function_hook=hook)
        e.hogehoge(a=1, b=10, c=100)
        assert check

    def test__classkwargs_function_hook(self, init_instance):
        check = []
        class clz:
            def hogehoge(self,a,b,c):
                if a==1 and b==10 and c==100:
                    check.append('checked')
        c = clz()
        d, caller = dumps(c, snippet_share_only=False, return_caller=True)

        class hook(UnsirializeFunctionHook):
            def function_call(instanceid:int, name:str, args:tuple, kwargs:dict):
                return caller.function_call(instanceid, name, args, kwargs)
        
        e = loads(d, function_hook=hook)
        e.hogehoge(a=1, b=10, c=100)
        assert check==['checked']

    def test__simpleargskwargs_function_hook(self, init_instance):
        check = False
        def f(a,b,c):
            nonlocal check
            if a==1 and b==10 and c==100:
                check = True
        clz = types.new_class(f'test__serialize_dump_1', (object,))
        c = clz()
        c.__setattr__('hogehoge',f)
        d, caller = dumps(c, snippet_share_only=False, return_caller=True)

        class hook(UnsirializeFunctionHook):
            def function_call(instanceid:int, name:str, args:tuple, kwargs:dict):
                return caller.function_call(instanceid, name, args, kwargs)
        
        e = loads(d, function_hook=hook)
        e.hogehoge(1, b=10, c=100)
        assert check

    def test__classargskwargs_function_hook(self, init_instance):
        check = []
        class clz:
            def hogehoge(self,a,b,c):
                if a==1 and b==10 and c==100:
                    check.append('checked')
        c = clz()
        d, caller = dumps(c, snippet_share_only=False, return_caller=True)

        class hook(UnsirializeFunctionHook):
            def function_call(instanceid:int, name:str, args:tuple, kwargs:dict):
                return caller.function_call(instanceid, name, args, kwargs)
        
        e = loads(d, function_hook=hook)
        e.hogehoge(1, b=10, c=100)
        assert check==['checked']

    def test__value_simple_function_hook(self, init_instance):
        def f():
            return 'checked'
        clz = types.new_class(f'test__serialize_dump_1', (object,))
        c = clz()
        c.__setattr__('hogehoge',f)
        d, caller = dumps(c, snippet_share_only=False, return_caller=True)

        class hook(UnsirializeFunctionHook):
            def function_call(instanceid:int, name:str, args:tuple, kwargs:dict):
                return caller.function_call(instanceid, name, args, kwargs)
        
        e = loads(d, function_hook=hook)
        r = e.hogehoge()
        assert r == 'checked'

    def test__value_class_function_hook(self, init_instance):
        class clz:
            def hogehoge(self):
                return 'checked'
        c = clz()
        d, caller = dumps(c, snippet_share_only=False, return_caller=True)

        class hook(UnsirializeFunctionHook):
            def function_call(instanceid:int, name:str, args:tuple, kwargs:dict):
                return caller.function_call(instanceid, name, args, kwargs)
        
        e = loads(d, function_hook=hook)
        r = e.hogehoge()
        assert r == 'checked'
