import pytest
from typing import List, Dict, Tuple, Union, Callable, Optional
import types
import json
import time
import remoteexec
from remoteexec.communicate import *
from remoteexec.communicate.exceptions import *
from remoteexec.communicate.serializer import loads, dumps


class TestSerializerDumps:
    @pytest.fixture
    def init_instance(self):
        pass

    def test__single_dump(self, init_instance):
        clz = types.new_class(f'test__serialize_dump_1', (object,))
        c = clz()
        c.__setattr__('hogehoge','value1')
        d = dumps(c, snippet_share_only=False)
        assert d=={'object': id(c), 'instance': 
                    {id(c): {'__type__': 'object', 'hogehoge': {'type': 'native', 'value': 'value1'}}}}
        j = json.dumps(d)

    def test__singleclass_dump(self, init_instance):
        class single_dump:
            def __init__(self):
                self.hogehoge = 'value1'
        c = single_dump()
        d = dumps(c, snippet_share_only=False)
        assert d=={'object': id(c), 'instance': 
                    {id(c): {'__type__': 'object', 'hogehoge': {'type': 'native', 'value': 'value1'}}}}
        j = json.dumps(d)

    def test__native_dump(self, init_instance):
        d = dumps(123, snippet_share_only=False)
        assert d=={'object': 0, 'value':123}
        d = dumps(123.456, snippet_share_only=False)
        assert d=={'object': 0, 'value':123.456}
        d = dumps('789', snippet_share_only=False)
        assert d=={'object': 0, 'value':'789'}
        d = dumps(None, snippet_share_only=False)
        assert d=={'object': 0, 'value':None}
        d = dumps(True, snippet_share_only=False)
        assert d=={'object': 0, 'value':True}

    def test__nativetypeintype_dump(self, init_instance):
        c = [2,2.01,None,True]
        d = dumps(c, snippet_share_only=False)
        assert d == {'object': id(c), 'instance': {id(c):{'__type__': 'list', '0': {'type': 'native', 'value': 2}, '1': {'type': 'native', 'value': 2.01}, '2': {'type': 'native', 'value': None}, '3': {'type': 'native', 'value': True}}}}
        c = (2,2.01,None,True)
        d = dumps(c, snippet_share_only=False)
        assert d == {'object': id(c), 'instance': {id(c):{'__type__': 'tuple', '0': {'type': 'native', 'value': 2}, '1': {'type': 'native', 'value': 2.01}, '2': {'type': 'native', 'value': None}, '3': {'type': 'native', 'value': True}}}}
        c = {"A":2,"B":2.01,"C":None,"D":True}
        d = dumps(c, snippet_share_only=False)
        assert d == {'object': id(c), 'instance': {id(c):{'__type__': 'dict', 'keys': [{'type': 'native', 'value': 'A'}, {'type': 'native', 'value': 'B'}, {'type': 'native', 'value': 'C'}, {'type': 'native', 'value': 'D'}], 'values': [{'type': 'native', 'value': 2}, {'type': 'native', 'value': 2.01}, {'type': 'native', 'value': None}, {'type': 'native', 'value': True}]}}}
    
    def test__tuplekeydict_dump(self, init_instance):
        k1 = (1,2)
        k2 = (4,5)
        c = {}
        c[k1] = 'value1'
        c[k2] = k1
        c[0] = 10
        d = dumps(c, snippet_share_only=False)
        assert d=={'object': id(c), 'instance': 
                    {id(k1): {'__type__': 'tuple', '0': {'type': 'native', 'value': 1}, '1': {'type': 'native', 'value': 2}},
                     id(k2): {'__type__': 'tuple', '0': {'type': 'native', 'value': 4}, '1': {'type': 'native', 'value': 5}},
                     id(c): {'__type__': 'dict', 'keys': [{'type': 'pointer', 'value': id(k1)},{'type': 'pointer', 'value': id(k2)},{'type': 'native', 'value': 0}],
                                                 'values': [{'type': 'native', 'value': 'value1'}, {'type': 'pointer', 'value': id(k1)}, {'type': 'native', 'value': 10}]}}}
        j = json.dumps(d)

    def test__singlehierarchy_dump(self, init_instance):
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
        assert d=={'object': id(c1), 'instance': 
                    {id(c1): {'__type__': 'object', 'hierarchy1': {'type': 'pointer', 'value': id(c2)}, 'hogehoge1': {'type': 'native', 'value': 'value1'}},
                     id(c2): {'__type__': 'object', 'hierarchy2': {'type': 'pointer', 'value': id(c3)}, 'hogehoge2': {'type': 'native', 'value': 'value2'}},
                     id(c3): {'__type__': 'object', 'hogehoge3': {'type': 'native', 'value': 'value3'}}}}
        j = json.dumps(d)

    def test__singlecirculation_dump(self, init_instance):
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
        assert d=={'object': id(c1), 'instance': 
                    {id(c1): {'__type__': 'object', 'hierarchy1': {'type': 'pointer', 'value': id(c2)}, 'hogehoge1': {'type': 'native', 'value': 'value1'}},
                     id(c2): {'__type__': 'object', 'hierarchy2': {'type': 'pointer', 'value': id(c3)}, 'hogehoge2': {'type': 'native', 'value': 'value2'}},
                     id(c3): {'__type__': 'object', 'hierarchy3': {'type': 'pointer', 'value': id(c1)}, 'hogehoge3': {'type': 'native', 'value': 'value3'}}}}
        j = json.dumps(d)

    def test__types_dump(self, init_instance):
        clz = types.new_class(f'test__serialize_dump_1', (object,))
        c = clz()
        c.__setattr__('hogehogestr','value1')
        c.__setattr__('hogehogeint',1)
        c.__setattr__('hogehogefloat',2.001)
        c.__setattr__('hogehogedict',{'a':0,'b':'B'})
        c.__setattr__('hogehogelist',[1,2,3])
        c.__setattr__('hogehogeset',{4,5,6})
        c.__setattr__('hogehogetuple',(7,8,9))
        c.__setattr__('hogehogeNone',None)
        c.__setattr__('hogehogebool',True)
        d = dumps(c, snippet_share_only=False)
        assert d=={'object': id(c), 'instance': {
                    id(c): {'__type__': 'object', 'hogehogestr': {'type': 'native', 'value': 'value1'}, 
                                                  'hogehogeint': {'type': 'native', 'value': 1},
                                                  'hogehogefloat': {'type': 'native', 'value': 2.001}, 
                                                  'hogehogeNone': {'type': 'native', 'value': None}, 
                                                  'hogehogebool': {'type': 'native', 'value': True}, 
                                                  'hogehogedict': {'type': 'pointer', 'value': id(c.hogehogedict)},
                                                  'hogehogelist': {'type': 'pointer', 'value': id(c.hogehogelist)}, 
                                                  'hogehogeset': {'type': 'pointer', 'value': id(c.hogehogeset)},
                                                  'hogehogetuple': {'type': 'pointer', 'value': id(c.hogehogetuple)}},
                    id(c.hogehogedict): {'__type__': 'dict', 'keys': [{'type': 'native', 'value': 'a'}, {'type': 'native', 'value': 'b'}], 'values': [{'type': 'native', 'value': 0}, {'type': 'native', 'value': 'B'}]},
                    id(c.hogehogelist): {'__type__': 'list', '0': {'type': 'native', 'value': 1}, '1': {'type': 'native', 'value': 2}, '2': {'type': 'native', 'value': 3}},
                    id(c.hogehogeset): {'__type__': 'set', '0': {'type': 'native', 'value': 4}, '1': {'type': 'native', 'value': 5}, '2': {'type': 'native', 'value': 6}},
                    id(c.hogehogetuple): {'__type__': 'tuple', '0': {'type': 'native', 'value': 7}, '1': {'type': 'native', 'value': 8}, '2': {'type': 'native', 'value': 9}}}}
        j = json.dumps(d)

    def test__class_dump(self, init_instance):
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
        assert d=={'object': id(c1), 'instance': {
                    id(c1): {'__type__': 'object', 'c': {'type': 'pointer', 'value': id(c2)}},
                    id(c2): {'__type__': 'object', 'c': {'type': 'native', 'value': 10}, 'hoge': {'type': 'native', 'value': 'hoge'}}}}
        j = json.dumps(d)

    def test__classcirculation_dump(self, init_instance):
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
        assert d=={'object': id(c1), 'instance': {
                    id(c1): {'__type__': 'object', 'c': {'type': 'pointer', 'value': id(c2)}},
                    id(c2): {'__type__': 'object', 'c': {'type': 'pointer', 'value': id(c1)}, 'hoge': {'type': 'native', 'value': 'hoge'}}}}
        j = json.dumps(d)

    def test__shareclass_dump(self, init_instance):
        @snippet_share
        class clz1:
            def __init__(self, c):
                self.c = c
        @snippet_share
        class clz2:
            def __init__(self, c):
                self.c = c
                self.hoge = 'hoge'
        class clz3:
            def __init__(self, c):
                self.c = c
                self.hogehoge = 'hogehoge'
        c3 = clz3(10)
        c2 = clz2(c3)
        c1 = clz1(c2)
        d = dumps(c1, snippet_share_only=True)
        assert d=={'object': id(c1), 'instance': {
                    id(c1): {'__type__': 'object', 'c': {'type': 'pointer', 'value': id(c2)}},
                    id(c2): {'__type__': 'object', 'hoge': {'type': 'native', 'value': 'hoge'}}}}
        j = json.dumps(d)

    def test__depthclass_dump(self, init_instance):
        @snippet_share
        class clz1:
            def __init__(self, c):
                self.c = c
        @snippet_share
        class clz2:
            def __init__(self, c):
                self.c = c
                self.hoge = 'hoge'
        @snippet_share
        class clz3:
            def __init__(self, c):
                self.c = c
                self.hogehoge = 'hogehoge'
        c3 = clz3(10)
        c2 = clz2(c3)
        c1 = clz1(c2)
        d = dumps(c1, snippet_share_only=True, dump_object_depth=2)
        assert d=={'object': id(c1), 'instance': {
                    id(c1): {'__type__': 'object', 'c': {'type': 'pointer', 'value': id(c2)}},
                    id(c2): {'__type__': 'object', 'hoge': {'type': 'native', 'value': 'hoge'}}}}
        j = json.dumps(d)

    def test__dicthierarchy_dump(self, init_instance):
        c1 = {}
        c2 = {}
        c3 = {}
        c1['hogehoge1'] = 'value1'
        c1['hierarchy1'] = c2
        c2['hogehoge2'] = 'value2'
        c2['hierarchy2'] = c3
        c3['hogehoge3'] = 'value3'
        d = dumps(c1, snippet_share_only=False)
        assert d=={'object': id(c1), 'instance': 
                    {id(c1): {'__type__': 'dict', 'keys':[{'type': 'native', 'value': 'hogehoge1'}, {'type': 'native', 'value': 'hierarchy1'}],
                                                  'values': [{'type': 'native', 'value': 'value1'}, {'type': 'pointer', 'value': id(c2)}]},
                     id(c2): {'__type__': 'dict', 'keys':[{'type': 'native', 'value': 'hogehoge2'}, {'type': 'native', 'value': 'hierarchy2'}],
                                                  'values': [{'type': 'native', 'value': 'value2'}, {'type': 'pointer', 'value': id(c3)}]},
                     id(c3): {'__type__': 'dict', 'keys':[{'type': 'native', 'value': 'hogehoge3'}],
                                                  'values': [{'type': 'native', 'value': 'value3'}]}}}
        j = json.dumps(d)

    def test__listhierarchy_dump(self, init_instance):
        c1 = []
        c2 = []
        c3 = []
        c1.append('value1')
        c1.append(c2)
        c2.append('value2')
        c2.append(c3)
        c3.append('value3')
        d = dumps(c1, snippet_share_only=False)
        assert d=={'object': id(c1), 'instance': 
                    {id(c1): {'__type__': 'list', '1': {'type': 'pointer', 'value': id(c2)}, '0': {'type': 'native', 'value': 'value1'}},
                     id(c2): {'__type__': 'list', '1': {'type': 'pointer', 'value': id(c3)}, '0': {'type': 'native', 'value': 'value2'}},
                     id(c3): {'__type__': 'list', '0': {'type': 'native', 'value': 'value3'}}}}
        j = json.dumps(d)

    def test__tuplehierarchy_dump(self, init_instance):
        c = {'hogehoge1':'value1','hierarchy1':('value2',('value3',0))}
        d = dumps(c, snippet_share_only=False)
        assert d=={'object': id(c), 'instance': 
                    {id(c): {'__type__': 'dict', 'keys': [{'type': 'native', 'value': 'hogehoge1'}, {'type': 'native', 'value': 'hierarchy1'}],
                                                 'values': [{'type': 'native', 'value': 'value1'}, {'type': 'pointer', 'value': id(c['hierarchy1'])}]},
                     id(c['hierarchy1']): {'__type__': 'tuple', '1': {'type': 'pointer', 'value': id(c['hierarchy1'][1])}, '0': {'type': 'native', 'value': 'value2'}},
                     id(c['hierarchy1'][1]): {'__type__': 'tuple', '0': {'type': 'native', 'value': 'value3'}, '1': {'type': 'native', 'value': 0}}}}
        j = json.dumps(d)

    def test__simple_return_caller(self, init_instance):
        check = False
        def f():
            nonlocal check
            check = True
        clz = types.new_class(f'test__serialize_dump_1', (object,))
        c = clz()
        c.__setattr__('hogehoge',f)
        d, caller = dumps(c, snippet_share_only=False, return_caller=True)
        assert d=={'object': id(c), 'instance': 
                    {id(c): {'__type__': 'object', 'hogehoge': {'type': 'function'}}}}
        j = json.dumps(d)
        caller.function_call(id(c), 'hogehoge', tuple(), {})
        assert check

    def test__class_return_caller(self, init_instance):
        check = []
        class clz:
            def hogehoge(self):
                check.append('checked')
        c = clz()
        d, caller = dumps(c, snippet_share_only=False, return_caller=True)
        assert d=={'object': id(c), 'instance': 
                    {id(c): {'__type__': 'object', 'hogehoge': {'type': 'function'}}}}
        j = json.dumps(d)
        caller.function_call(id(c), 'hogehoge', tuple(), {})
        assert check==['checked']

    def test__simpleargs_return_caller(self, init_instance):
        check = False
        def f(a,b,c):
            nonlocal check
            if a==1 and b==10 and c==100:
                check = True
        clz = types.new_class(f'test__serialize_dump_1', (object,))
        c = clz()
        c.__setattr__('hogehoge',f)
        d, caller = dumps(c, snippet_share_only=False, return_caller=True)
        assert d=={'object': id(c), 'instance': 
                    {id(c): {'__type__': 'object', 'hogehoge': {'type': 'function'}}}}
        j = json.dumps(d)
        caller.function_call(id(c), 'hogehoge', (1,10,100), {})
        assert check

    def test__classargs_return_caller(self, init_instance):
        check = []
        class clz:
            def hogehoge(self,a,b,c):
                if a==1 and b==10 and c==100:
                    check.append('checked')
        c = clz()
        d, caller = dumps(c, snippet_share_only=False, return_caller=True)
        assert d=={'object': id(c), 'instance': 
                    {id(c): {'__type__': 'object', 'hogehoge': {'type': 'function'}}}}
        j = json.dumps(d)
        caller.function_call(id(c), 'hogehoge', (1,10,100), {})
        assert check==['checked']

    def test__simplekwargs_return_caller(self, init_instance):
        check = False
        def f(a,b,c):
            nonlocal check
            if a==1 and b==10 and c==100:
                check = True
        clz = types.new_class(f'test__serialize_dump_1', (object,))
        c = clz()
        c.__setattr__('hogehoge',f)
        d, caller = dumps(c, snippet_share_only=False, return_caller=True)
        assert d=={'object': id(c), 'instance': 
                    {id(c): {'__type__': 'object', 'hogehoge': {'type': 'function'}}}}
        j = json.dumps(d)
        caller.function_call(id(c), 'hogehoge', tuple(), {'a':1,'b':10,'c':100})
        assert check

    def test__classkwargs_return_caller(self, init_instance):
        check = []
        class clz:
            def hogehoge(self,a,b,c):
                if a==1 and b==10 and c==100:
                    check.append('checked')
        c = clz()
        d, caller = dumps(c, snippet_share_only=False, return_caller=True)
        assert d=={'object': id(c), 'instance': 
                    {id(c): {'__type__': 'object', 'hogehoge': {'type': 'function'}}}}
        j = json.dumps(d)
        caller.function_call(id(c), 'hogehoge', tuple(), {'a':1,'b':10,'c':100})
        assert check==['checked']

    def test__simpleargskwargs_return_caller(self, init_instance):
        check = False
        def f(a,b,c):
            nonlocal check
            if a==1 and b==10 and c==100:
                check = True
        clz = types.new_class(f'test__serialize_dump_1', (object,))
        c = clz()
        c.__setattr__('hogehoge',f)
        d, caller = dumps(c, snippet_share_only=False, return_caller=True)
        assert d=={'object': id(c), 'instance': 
                    {id(c): {'__type__': 'object', 'hogehoge': {'type': 'function'}}}}
        j = json.dumps(d)
        caller.function_call(id(c), 'hogehoge', (1,10), {'c':100})
        assert check

    def test__classargskwargs_return_caller(self, init_instance):
        check = []
        class clz:
            def hogehoge(self,a,b,c):
                if a==1 and b==10 and c==100:
                    check.append('checked')
        c = clz()
        d, caller = dumps(c, snippet_share_only=False, return_caller=True)
        assert d=={'object': id(c), 'instance': 
                    {id(c): {'__type__': 'object', 'hogehoge': {'type': 'function'}}}}
        j = json.dumps(d)
        caller.function_call(id(c), 'hogehoge', (1,10), {'c':100})
        assert check==['checked']

    def test__value_simple_return_caller(self, init_instance):
        def f():
            return 'checked'
        clz = types.new_class(f'test__serialize_dump_1', (object,))
        c = clz()
        c.__setattr__('hogehoge',f)
        d, caller = dumps(c, snippet_share_only=False, return_caller=True)
        assert d=={'object': id(c), 'instance': 
                    {id(c): {'__type__': 'object', 'hogehoge': {'type': 'function'}}}}
        j = json.dumps(d)
        r = caller.function_call(id(c), 'hogehoge', tuple(), {})
        assert r == 'checked'

    def test__value_class_return_caller(self, init_instance):
        class clz:
            def hogehoge(self):
                return 'checked'
        c = clz()
        d, caller = dumps(c, snippet_share_only=False, return_caller=True)
        assert d=={'object': id(c), 'instance': 
                    {id(c): {'__type__': 'object', 'hogehoge': {'type': 'function'}}}}
        j = json.dumps(d)
        r = caller.function_call(id(c), 'hogehoge', tuple(), {})
        assert r == 'checked'
