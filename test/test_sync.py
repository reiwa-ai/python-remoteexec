import pytest
from typing import List, Dict, Tuple, Union, Callable, Optional
import types
import json
import time
import remoteexec
from remoteexec.communicate import *
from remoteexec.communicate.serializer import loads, dumps
from remoteexec.communicate.sync import *


class TestDiff:
    @pytest.fixture
    def init_instance(self):
        pass

    def test__simple_diff(self, init_instance):
        clz1 = types.new_class(f'test__simple_diff_1', (object,))
        clz2 = types.new_class(f'test__simple_diff_2', (object,))
        c1 = clz1()
        c2 = clz2()
        c1.__setattr__('hogehoge1','value1')
        c2.__setattr__('hogehoge2','value2')
        d1 = dumps(c1, snippet_share_only=False)
        d2 = dumps(c2, snippet_share_only=False)
        e = diff(d1, d2)
        assert e.updated_member == []
        assert e.created_member == []
        assert e.deleted_member == []
        assert len(e.created_instance) == 1
        assert len(e.deleted_instance) == 1
        assert e.created_instance[0].instance_id == id(c2)
        assert e.created_instance[0].value == {'__type__': 'object', 'hogehoge2': {'type': 'native', 'value': 'value2'}}
        assert e.deleted_instance[0].instance_id == id(c1)
        assert e.deleted_instance[0].value == {'__type__': 'object', 'hogehoge1': {'type': 'native', 'value': 'value1'}}

    def test__update_diff(self, init_instance):
        clz = types.new_class(f'test__update_diff', (object,))
        c = clz()
        c.__setattr__('hogehoge','value1')
        d1 = dumps(c, snippet_share_only=False)
        c.__setattr__('hogehoge','value2')
        d2 = dumps(c, snippet_share_only=False)
        e = diff(d1, d2)
        assert len(e.updated_member) == 1
        assert e.updated_member[0].instance_id == id(c)
        assert e.updated_member[0].member_name == 'hogehoge'
        assert e.updated_member[0].value == {'type': 'native', 'value': 'value2'}
        assert e.created_member == []
        assert e.deleted_member == []
        assert e.created_instance == []
        assert e.deleted_instance == []

    def test__update_class_diff(self, init_instance):
        class update_diff:
            def __init__(self):
                self.hogehoge = 'value1'
        c = update_diff()
        d1 = dumps(c, snippet_share_only=False)
        c.hogehoge = 'value2'
        d2 = dumps(c, snippet_share_only=False)
        e = diff(d1, d2)
        assert len(e.updated_member) == 1
        assert e.updated_member[0].instance_id == id(c)
        assert e.updated_member[0].member_name == 'hogehoge'
        assert e.updated_member[0].value == {'type': 'native', 'value': 'value2'}
        assert e.created_member == []
        assert e.deleted_member == []
        assert e.created_instance == []
        assert e.deleted_instance == []

    def test__append_diff(self, init_instance):
        clz = types.new_class(f'test__append_diff', (object,))
        c = clz()
        c.__setattr__('hogehoge','value1')
        d1 = dumps(c, snippet_share_only=False)
        c.__setattr__('boohuu','value2')
        d2 = dumps(c, snippet_share_only=False)
        e = diff(d1, d2)
        assert e.updated_member == []
        assert len(e.created_member) == 1
        assert e.created_member[0].instance_id == id(c)
        assert e.created_member[0].member_name == 'boohuu'
        assert e.created_member[0].value == {'type': 'native', 'value': 'value2'}
        assert e.deleted_member == []
        assert e.created_instance == []
        assert e.deleted_instance == []

    def test__append_class_diff(self, init_instance):
        class append_diff:
            def __init__(self):
                self.hogehoge = 'value1'
        c = append_diff()
        d1 = dumps(c, snippet_share_only=False)
        c.boohuu = 'value2'
        d2 = dumps(c, snippet_share_only=False)
        e = diff(d1, d2)
        assert e.updated_member == []
        assert len(e.created_member) == 1
        assert e.created_member[0].instance_id == id(c)
        assert e.created_member[0].member_name == 'boohuu'
        assert e.created_member[0].value == {'type': 'native', 'value': 'value2'}
        assert e.deleted_member == []
        assert e.created_instance == []
        assert e.deleted_instance == []

    def test__remove_diff(self, init_instance):
        clz = types.new_class(f'test__remove_diff', (object,))
        c = clz()
        c.__setattr__('hogehoge','value1')
        c.__setattr__('boohuu','value2')
        d1 = dumps(c, snippet_share_only=False)
        del c.boohuu
        d2 = dumps(c, snippet_share_only=False)
        e = diff(d1, d2)
        assert e.updated_member == []
        assert e.created_member == []
        assert len(e.deleted_member) == 1
        assert e.deleted_member[0].instance_id == id(c)
        assert e.deleted_member[0].member_name == 'boohuu'
        assert e.deleted_member[0].value == {'type': 'native', 'value': 'value2'}
        assert e.created_instance == []
        assert e.deleted_instance == []

    def test__remove_class_diff(self, init_instance):
        class remove_diff:
            def __init__(self):
                self.hogehoge = 'value1'
                self.boohuu = 'value2'
        c = remove_diff()
        d1 = dumps(c, snippet_share_only=False)
        del c.boohuu
        d2 = dumps(c, snippet_share_only=False)
        e = diff(d1, d2)
        assert e.updated_member == []
        assert e.created_member == []
        assert len(e.deleted_member) == 1
        assert e.deleted_member[0].instance_id == id(c)
        assert e.deleted_member[0].member_name == 'boohuu'
        assert e.deleted_member[0].value == {'type': 'native', 'value': 'value2'}
        assert e.created_instance == []
        assert e.deleted_instance == []

    def test__appendinstance_diff(self, init_instance):
        clz1 = types.new_class(f'test__appendinstance_diff_1', (object,))
        clz2 = types.new_class(f'test__appendinstance_diff_2', (object,))
        c1 = clz1()
        c2 = clz2()
        c1.__setattr__('hogehoge1','value1')
        c2.__setattr__('boohuu','value2')
        d1 = dumps(c1, snippet_share_only=False)
        c1.__setattr__('hogehoge2',c2)
        d2 = dumps(c1, snippet_share_only=False)
        e = diff(d1, d2)
        assert e.updated_member == []
        assert e.created_member[0].instance_id == id(c1)
        assert e.created_member[0].member_name == 'hogehoge2'
        assert e.created_member[0].value == {'type': 'pointer', 'value': id(c2)}
        assert e.deleted_member == []
        assert len(e.created_instance) == 1
        assert e.created_instance[0].instance_id == id(c2)
        assert e.created_instance[0].value == {'__type__': 'object', 'boohuu': {'type': 'native', 'value': 'value2'}}
        assert e.deleted_instance == []

    def test__deleteinstance_diff(self, init_instance):
        clz1 = types.new_class(f'test__deleteinstance_diff_1', (object,))
        clz2 = types.new_class(f'test__deleteinstance_diff_2', (object,))
        c1 = clz1()
        c2 = clz2()
        c1.__setattr__('hogehoge1','value1')
        c2.__setattr__('boohuu','value2')
        c1.__setattr__('hogehoge2',c2)
        d1 = dumps(c1, snippet_share_only=False)
        del c1.hogehoge2
        d2 = dumps(c1, snippet_share_only=False)
        e = diff(d1, d2)
        assert e.updated_member == []
        assert e.created_member == []
        assert e.deleted_member[0].instance_id == id(c1)
        assert e.deleted_member[0].member_name == 'hogehoge2'
        assert e.deleted_member[0].value == {'type': 'pointer', 'value': id(c2)}
        assert e.created_instance == []
        assert len(e.deleted_instance) == 1
        assert e.deleted_instance[0].instance_id == id(c2)
        assert e.deleted_instance[0].value == {'__type__': 'object', 'boohuu': {'type': 'native', 'value': 'value2'}}


class TestDictDiff:
    @pytest.fixture
    def init_instance(self):
        pass

    def test__simple_dictdiff(self, init_instance):
        c = {"hogehoge":0}
        d1 = dumps(c, snippet_share_only=False)
        c["hogehoge"] = 1
        d2 = dumps(c, snippet_share_only=False)
        e = diff(d1, d2)
        assert e.updated_member[0].instance_id == id(c)
        assert e.updated_member[0].member_name == {'type': 'native', 'value': 'hogehoge'}
        assert e.updated_member[0].value == {'type': 'native', 'value': 1}
        assert e.created_member == []
        assert e.deleted_member == []
        assert e.created_instance == []
        assert e.deleted_instance == []

    def test__append_dictdiff(self, init_instance):
        c = {'hogehoge':'value1'}
        d1 = dumps(c, snippet_share_only=False)
        c['boohuu'] = 'value2'
        d2 = dumps(c, snippet_share_only=False)
        e = diff(d1, d2)
        assert e.updated_member == []
        assert len(e.created_member) == 1
        assert e.created_member[0].instance_id == id(c)
        assert e.created_member[0].member_name == {'type': 'native', 'value': 'boohuu'}
        assert e.created_member[0].value == {'type': 'native', 'value': 'value2'}
        assert e.deleted_member == []
        assert e.created_instance == []
        assert e.deleted_instance == []

    def test__append_class_dictdiff(self, init_instance):
        class append_diff:
            def __init__(self):
                self.hogehoge = 'value1'
        c = {'boohuu':'value2'}
        d1 = dumps(c, snippet_share_only=False)
        c2 = append_diff()
        c['hogehoge'] = c2
        d2 = dumps(c, snippet_share_only=False)
        e = diff(d1, d2)
        assert e.updated_member == []
        assert len(e.created_member) == 1
        assert e.created_member[0].instance_id == id(c)
        assert e.created_member[0].member_name == {'type': 'native', 'value': 'hogehoge'}
        assert e.created_member[0].value == {'type': 'pointer', 'value': id(c2)}
        assert e.deleted_member == []
        assert e.created_instance[0].instance_id == id(c2)
        assert e.created_instance[0].value == {'__type__': 'object', 'hogehoge': {'type': 'native', 'value': 'value1'}}
        assert e.deleted_instance == []

    def test__remove_dictdiff(self, init_instance):
        c = {'hogehoge':'value1', 'boohuu':'value2'}
        d1 = dumps(c, snippet_share_only=False)
        del c["boohuu"]
        d2 = dumps(c, snippet_share_only=False)
        e = diff(d1, d2)
        assert e.updated_member == []
        assert e.created_member == []
        assert len(e.deleted_member) == 1
        assert e.deleted_member[0].instance_id == id(c)
        assert e.deleted_member[0].member_name == {'type': 'native', 'value': 'boohuu'}
        assert e.deleted_member[0].value == {'type': 'native', 'value': 'value2'}
        assert e.created_instance == []
        assert e.deleted_instance == []

    def test__deleteinstance_dictdiff(self, init_instance):
        class append_diff:
            def __init__(self):
                self.hogehoge = 'value1'
        c2 = append_diff()
        c = {'boohuu':'value2','hogehoge':c2}
        d1 = dumps(c, snippet_share_only=False)
        del c['hogehoge']
        d2 = dumps(c, snippet_share_only=False)
        e = diff(d1, d2)
        assert e.updated_member == []
        assert e.created_member == []
        assert len(e.deleted_member) == 1
        assert e.deleted_member[0].instance_id == id(c)
        assert e.deleted_member[0].member_name == {'type': 'native', 'value': 'hogehoge'}
        assert e.deleted_member[0].value == {'type': 'pointer', 'value': id(c2)}
        assert e.created_instance == []
        assert e.deleted_instance[0].instance_id == id(c2)
        assert e.deleted_instance[0].value == {'__type__': 'object', 'hogehoge': {'type': 'native', 'value': 'value1'}}


class TestMarge:
    @pytest.fixture
    def init_instance(self):
        pass

    def test__simple_marge(self, init_instance):
        clz1 = types.new_class(f'test__simple_marge_1', (object,))
        clz2 = types.new_class(f'test__simple_marge_2', (object,))
        c1 = clz1()
        c2 = clz2()
        c1.__setattr__('hogehoge1','value1')
        c2.__setattr__('hogehoge2','value2')
        d1 = dumps(c1, snippet_share_only=False)
        d2 = dumps(c2, snippet_share_only=False)
        e = diff(d1, d2)
        clz3 = types.new_class(f'test__simple_marge_3', (object,))
        c3 = clz3()
        c3.__setattr__('hogehoge3','value3')
        d3 = dumps(c3, snippet_share_only=False)
        f = diff(d1, d3)
        m = marge(e, f)
        assert m.updated_member == []
        assert m.created_member == []
        assert m.deleted_member == []
        assert len(m.created_instance) == 2
        assert len(m.deleted_instance) == 1
        assert m.created_instance[0].value == {'__type__': 'object', 'hogehoge2': {'type': 'native', 'value': 'value2'}}
        assert m.created_instance[1].value == {'__type__': 'object', 'hogehoge3': {'type': 'native', 'value': 'value3'}}
        assert m.deleted_instance[0].value == {'__type__': 'object', 'hogehoge1': {'type': 'native', 'value': 'value1'}}

    def test__update_marge(self, init_instance):
        clz = types.new_class(f'test__update_marge', (object,))
        c = clz()
        c.__setattr__('hogehoge','value1')
        d1 = dumps(c, snippet_share_only=False)
        c.__setattr__('hogehoge','value2')
        d2 = dumps(c, snippet_share_only=False)
        e = diff(d1, d2)
        c.__setattr__('hogehoge','value3')
        d3 = dumps(c, snippet_share_only=False)
        f = diff(d1, d3)
        m = marge(e, f)
        assert len(m.updated_member) == 1
        assert m.updated_member[0].instance_id == id(c)
        assert m.updated_member[0].member_name == 'hogehoge'
        assert m.updated_member[0].value == {'type': 'native', 'value': 'value2'}
        assert m.created_member == []
        assert m.deleted_member == []
        assert m.created_instance == []
        assert m.deleted_instance == []

    def test__append_marge(self, init_instance):
        clz = types.new_class(f'test__append_marge', (object,))
        c = clz()
        c.__setattr__('hogehoge','value1')
        d1 = dumps(c, snippet_share_only=False)
        c.__setattr__('hogehoge','value2')
        d2 = dumps(c, snippet_share_only=False)
        e = diff(d1, d2)
        c.__setattr__('hogehoge3','value3')
        d3 = dumps(c, snippet_share_only=False)
        f = diff(d1, d3)
        m = marge(e, f)
        assert len(m.updated_member) == 1
        assert m.updated_member[0].instance_id == id(c)
        assert m.updated_member[0].member_name == 'hogehoge'
        assert m.updated_member[0].value == {'type': 'native', 'value': 'value2'}
        assert m.created_member[0].instance_id == id(c)
        assert m.created_member[0].member_name == 'hogehoge3'
        assert m.created_member[0].value == {'type': 'native', 'value': 'value3'}
        assert m.deleted_member == []
        assert m.created_instance == []
        assert m.deleted_instance == []

    def test__remove_marge(self, init_instance):
        clz = types.new_class(f'test__remove_marge', (object,))
        c = clz()
        c.__setattr__('hogehoge','value1')
        c.__setattr__('boohuu','value2')
        d1 = dumps(c, snippet_share_only=False)
        del c.boohuu
        d2 = dumps(c, snippet_share_only=False)
        e = diff(d1, d2)
        c.__setattr__('hogehoge','value3')
        d3 = dumps(c, snippet_share_only=False)
        f = diff(d1, d3)
        m = marge(e, f)
        assert len(m.updated_member) == 1
        assert m.updated_member[0].instance_id == id(c)
        assert m.updated_member[0].member_name == 'hogehoge'
        assert m.updated_member[0].value == {'type': 'native', 'value': 'value3'}
        assert m.created_member == []
        assert len(m.deleted_member) == 1
        assert m.deleted_member[0].instance_id == id(c)
        assert m.deleted_member[0].member_name == 'boohuu'
        assert m.deleted_member[0].value == {'type': 'native', 'value': 'value2'}
        assert m.created_instance == []
        assert m.deleted_instance == []

    def test__appendremove_marge(self, init_instance):
        clz = types.new_class(f'test__appendremove_marge', (object,))
        c = clz()
        c.__setattr__('hogehoge','value1')
        c.__setattr__('boohuu','value2')
        d1 = dumps(c, snippet_share_only=False)
        del c.boohuu
        d2 = dumps(c, snippet_share_only=False)
        e = diff(d1, d2)
        c.__setattr__('boohuu','value3')
        d3 = dumps(c, snippet_share_only=False)
        f = diff(d1, d3)
        m = marge(e, f)
        assert m.updated_member == []
        assert m.created_member == []
        assert len(m.deleted_member) == 1
        assert m.deleted_member[0].instance_id == id(c)
        assert m.deleted_member[0].member_name == 'boohuu'
        assert m.deleted_member[0].value == {'type': 'native', 'value': 'value2'}
        assert m.created_instance == []
        assert m.deleted_instance == []

    def test__removeappend_marge(self, init_instance):
        clz = types.new_class(f'test__removeappend_marge', (object,))
        c = clz()
        c.__setattr__('hogehoge','value1')
        c.__setattr__('boohuu','value2')
        d1 = dumps(c, snippet_share_only=False)
        del c.boohuu
        d2 = dumps(c, snippet_share_only=False)
        e = diff(d1, d2)
        c.__setattr__('boohuu','value3')
        d3 = dumps(c, snippet_share_only=False)
        f = diff(d1, d3)
        m = marge(f, e)
        assert len(m.updated_member) == 1
        assert m.updated_member[0].instance_id == id(c)
        assert m.updated_member[0].member_name == 'boohuu'
        assert m.updated_member[0].value == {'type': 'native', 'value': 'value3'}
        assert m.created_member == []
        assert m.deleted_member == []
        assert m.created_instance == []
        assert m.deleted_instance == []

    def test__appendinstance_marge(self, init_instance):
        clz1 = types.new_class(f'test__appendinstance_marge_1', (object,))
        clz2 = types.new_class(f'test__appendinstance_marge_2', (object,))
        clz3 = types.new_class(f'test__appendinstance_marge_3', (object,))
        c1 = clz1()
        c2 = clz2()
        c1.__setattr__('hogehoge1','value1')
        c2.__setattr__('boohuu','value2')
        d1 = dumps(c1, snippet_share_only=False)
        c1.__setattr__('hogehoge2',c2)
        d2 = dumps(c1, snippet_share_only=False)
        e = diff(d1, d2)
        c3 = clz3()
        c1.__setattr__('hogehoge3',c3)
        d3 = dumps(c1, snippet_share_only=False)
        f = diff(d1, d3)
        m = marge(e, f)
        assert m.updated_member == []
        assert len(m.created_member) == 2
        assert m.created_member[0].instance_id == id(c1)
        assert m.created_member[0].member_name == 'hogehoge2'
        assert m.created_member[0].value == {'type': 'pointer', 'value': id(c2)}
        assert m.created_member[1].instance_id == id(c1)
        assert m.created_member[1].member_name == 'hogehoge3'
        assert m.created_member[1].value == {'type': 'pointer', 'value': id(c3)}
        assert m.deleted_member == []
        assert len(m.created_instance) == 2
        assert m.created_instance[0].instance_id == id(c2)
        assert m.created_instance[0].value == {'__type__': 'object', 'boohuu': {'type': 'native', 'value': 'value2'}}
        assert m.created_instance[1].instance_id == id(c3)
        assert m.created_instance[1].value == {'__type__': 'object'}
        assert m.deleted_instance == []

    def test__updateinstance_marge(self, init_instance):
        clz1 = types.new_class(f'test__appendinstance_marge_1', (object,))
        clz2 = types.new_class(f'test__appendinstance_marge_2', (object,))
        clz3 = types.new_class(f'test__appendinstance_marge_3', (object,))
        c1 = clz1()
        c2 = clz2()
        c1.__setattr__('hogehoge1','value1')
        c2.__setattr__('boohuu','value2')
        d1 = dumps(c1, snippet_share_only=False)
        c1.__setattr__('hogehoge2',c2)
        d2 = dumps(c1, snippet_share_only=False)
        e = diff(d1, d2)
        c3 = clz3()
        c1.__setattr__('hogehoge2',c3)
        d3 = dumps(c1, snippet_share_only=False)
        f = diff(d1, d3)
        m = marge(e, f)
        assert m.updated_member == []
        assert len(m.created_member) == 1
        assert m.created_member[0].instance_id == id(c1)
        assert m.created_member[0].member_name == 'hogehoge2'
        assert m.created_member[0].value == {'type': 'pointer', 'value': id(c2)}
        assert m.deleted_member == []
        assert len(m.created_instance) == 2
        assert m.created_instance[0].instance_id == id(c2)
        assert m.created_instance[0].value == {'__type__': 'object', 'boohuu': {'type': 'native', 'value': 'value2'}}
        assert m.created_instance[1].instance_id == id(c3)
        assert m.created_instance[1].value == {'__type__': 'object'}
        assert m.deleted_instance == []

    def test__deleteinstance_marge(self, init_instance):
        clz1 = types.new_class(f'test__deleteinstance_marge_1', (object,))
        clz2 = types.new_class(f'test__deleteinstance_marge_2', (object,))
        clz3 = types.new_class(f'test__deleteinstance_marge_3', (object,))
        c1 = clz1()
        c2 = clz2()
        c3 = clz3()
        c1.__setattr__('hogehoge2',c2)
        c1.__setattr__('hogehoge3',c3)
        d1 = dumps(c1, snippet_share_only=False)
        del c1.hogehoge2
        d2 = dumps(c1, snippet_share_only=False)
        e = diff(d1, d2)
        c1.__setattr__('hogehoge2',c2)
        c1.__setattr__('hogehoge3',c3)
        del c1.hogehoge3
        d3 = dumps(c1, snippet_share_only=False)
        f = diff(d1, d3)
        m = marge(e, f)
        assert m.updated_member == []
        assert m.created_member == []
        assert len(m.deleted_member) == 2
        assert m.deleted_member[0].instance_id == id(c1)
        assert m.deleted_member[0].member_name == 'hogehoge2'
        assert m.deleted_member[0].value == {'type': 'pointer', 'value': id(c2)}
        assert m.deleted_member[1].instance_id == id(c1)
        assert m.deleted_member[1].member_name == 'hogehoge3'
        assert m.deleted_member[1].value == {'type': 'pointer', 'value': id(c3)}
        assert m.created_instance == []
        assert len(m.deleted_instance) == 2
        assert m.deleted_instance[0].instance_id == id(c2)
        assert m.deleted_instance[0].value == {'__type__': 'object'}
        assert m.deleted_instance[1].instance_id == id(c3)
        assert m.deleted_instance[1].value == {'__type__': 'object'}

    def test__deleteinstanceduplicate_marge(self, init_instance):
        clz1 = types.new_class(f'test__deleteinstance_marge_1', (object,))
        clz2 = types.new_class(f'test__deleteinstance_marge_2', (object,))
        clz3 = types.new_class(f'test__deleteinstance_marge_3', (object,))
        c1 = clz1()
        c2 = clz2()
        c3 = clz3()
        c1.__setattr__('hogehoge2',c2)
        c1.__setattr__('hogehoge3',c3)
        d1 = dumps(c1, snippet_share_only=False)
        del c1.hogehoge2
        d2 = dumps(c1, snippet_share_only=False)
        e = diff(d1, d2)
        c1.__setattr__('hogehoge2',c2)
        c1.__setattr__('hogehoge3',c3)
        del c1.hogehoge2
        d3 = dumps(c1, snippet_share_only=False)
        f = diff(d1, d3)
        m = marge(e, f)
        assert m.updated_member == []
        assert m.created_member == []
        assert len(m.deleted_member) == 1
        assert m.deleted_member[0].instance_id == id(c1)
        assert m.deleted_member[0].member_name == 'hogehoge2'
        assert m.deleted_member[0].value == {'type': 'pointer', 'value': id(c2)}
        assert m.created_instance == []
        assert len(m.deleted_instance) == 1
        assert m.deleted_instance[0].instance_id == id(c2)
        assert m.deleted_instance[0].value == {'__type__': 'object'}



