import pytest
from typing import List, Dict, Tuple, Union, Callable, Optional
import types
import json
import time
import remoteexec
from remoteexec.communicate import *
from remoteexec.communicate.serializer import loads, dumps
from remoteexec.communicate.sync import *


class TestSimpleApply:
    @pytest.fixture
    def init_instance(self):
        pass

    def test__update_apply(self, init_instance):
        clz = types.new_class(f'test__simple_apply', (object,))
        c = clz()
        c.__setattr__('hogehoge','value1')
        a = SyncSharedObject(updated_member = [SyncInstanceMember(instance_id=id(c), member_name='hogehoge', value={'type': 'native', 'value': 'value2'})],
                             created_member = [],
                             deleted_member = [],
                             created_instance = [],
                             deleted_instance = [])
        apply_unsirial(c, a)
        assert c.hogehoge == 'value2'
        assert [d for d in dir(c) if not d.startswith('__')] == ['hogehoge']

    def test__update_class_apply(self, init_instance):
        class update_apply:
            def __init__(self):
                self.hogehoge = 'value1'
        c = update_apply()
        a = SyncSharedObject(updated_member = [SyncInstanceMember(instance_id=id(c), member_name='hogehoge', value={'type': 'native', 'value': 'value2'})],
                             created_member = [],
                             deleted_member = [],
                             created_instance = [],
                             deleted_instance = [])
        apply_unsirial(c, a)
        assert c.hogehoge == 'value2'
        assert [d for d in dir(c) if not d.startswith('__')] == ['hogehoge']

    def test__create_apply(self, init_instance):
        clz = types.new_class(f'test__create_apply', (object,))
        c = clz()
        c.__setattr__('hogehoge','value1')
        a = SyncSharedObject(updated_member = [],
                             created_member = [SyncInstanceMember(instance_id=id(c), member_name='hogehoge2', value={'type': 'native', 'value': 'value2'})],
                             deleted_member = [],
                             created_instance = [],
                             deleted_instance = [])
        apply_unsirial(c, a)
        assert c.hogehoge == 'value1'
        assert c.hogehoge2 == 'value2'
        assert [d for d in dir(c) if not d.startswith('__')] == ['hogehoge','hogehoge2']

    def test__create_class_apply(self, init_instance):
        class create_apply:
            def __init__(self):
                self.hogehoge = 'value1'
        c = create_apply()
        a = SyncSharedObject(updated_member = [],
                             created_member = [SyncInstanceMember(instance_id=id(c), member_name='hogehoge2', value={'type': 'native', 'value': 'value2'})],
                             deleted_member = [],
                             created_instance = [],
                             deleted_instance = [])
        apply_unsirial(c, a)
        assert c.hogehoge == 'value1'
        assert c.hogehoge2 == 'value2'
        assert [d for d in dir(c) if not d.startswith('__')] == ['hogehoge','hogehoge2']

    def test__remove_apply(self, init_instance):
        clz = types.new_class(f'test__remove_apply', (object,))
        c = clz()
        c.__setattr__('hogehoge','value1')
        c.__setattr__('hogehoge2','value2')
        a = SyncSharedObject(updated_member = [],
                             created_member = [],
                             deleted_member = [SyncInstanceMember(instance_id=id(c), member_name='hogehoge2', value={'type': 'native', 'value': 'value2'})],
                             created_instance = [],
                             deleted_instance = [])
        apply_unsirial(c, a)
        assert c.hogehoge == 'value1'
        try:
            print(c.hogehoge2)
            assert False
        except AttributeError:
            pass
        assert [d for d in dir(c) if not d.startswith('__')] == ['hogehoge']

    def test__remove_class_apply(self, init_instance):
        class remove_apply:
            def __init__(self):
                self.hogehoge = 'value1'
                self.hogehoge2 = 'value2'
        c = remove_apply()
        a = SyncSharedObject(updated_member = [],
                             created_member = [],
                             deleted_member = [SyncInstanceMember(instance_id=id(c), member_name='hogehoge2', value={'type': 'native', 'value': 'value2'})],
                             created_instance = [],
                             deleted_instance = [])
        apply_unsirial(c, a)
        assert c.hogehoge == 'value1'
        try:
            print(c.hogehoge2)
            assert False
        except AttributeError:
            pass
        assert [d for d in dir(c) if not d.startswith('__')] == ['hogehoge']

    def test__createinstance_apply(self, init_instance):
        clz = types.new_class(f'test__create_apply', (object,))
        c = clz()
        c.__setattr__('hogehoge','value1')
        a = SyncSharedObject(updated_member = [],
                             created_member = [SyncInstanceMember(instance_id=id(c), member_name='hogehoge2', value={'type': 'pointer', 'value': 1234})],
                             deleted_member = [],
                             created_instance = [SyncInstance(instance_id=1234, value={'__type__': 'object'})],
                             deleted_instance = [])
        apply_unsirial(c, a)
        assert c.hogehoge == 'value1'
        assert [d for d in dir(c.hogehoge2) if not d.startswith('__')] == []

    def test__createinstancemember_apply(self, init_instance):
        clz = types.new_class(f'test__create_apply_1', (object,))
        c = clz()
        c.__setattr__('hogehoge','value1')
        a = SyncSharedObject(updated_member = [],
                             created_member = [SyncInstanceMember(instance_id=id(c), member_name='hogehoge2', value={'type': 'pointer', 'value': 1234})],
                             deleted_member = [],
                             created_instance = [SyncInstance(instance_id=1234, value={'__type__': 'object', 'boohoo':{'type': 'native', 'value': 'value2'}})],
                             deleted_instance = [])
        apply_unsirial(c, a)
        assert c.hogehoge == 'value1'
        assert [d for d in dir(c.hogehoge2) if not d.startswith('__')] == ['boohoo']
        assert c.hogehoge2.boohoo == 'value2'

    def test__createinstancepointer_apply(self, init_instance):
        clz = types.new_class(f'test__create_apply', (object,))
        c = clz()
        c.__setattr__('hogehoge','value1')
        a = SyncSharedObject(updated_member = [],
                             created_member = [SyncInstanceMember(instance_id=id(c), member_name='hogehoge2', value={'type': 'pointer', 'value': 1234})],
                             deleted_member = [],
                             created_instance = [SyncInstance(instance_id=1234, value={'__type__': 'object', 'hogehoge3':{'type': 'pointer', 'value': 5678}}), SyncInstance(instance_id=5678, value={'__type__': 'object', 'boohoo':{'type': 'native', 'value': 'value2'}})],
                             deleted_instance = [])
        apply_unsirial(c, a)
        assert c.hogehoge == 'value1'
        assert [d for d in dir(c.hogehoge2) if not d.startswith('__')] == ['hogehoge3']
        assert c.hogehoge2.hogehoge3.boohoo == 'value2'
        assert [d for d in dir(c.hogehoge2.hogehoge3) if not d.startswith('__')] == ['boohoo']

    def test__createinstancepointerclass_apply(self, init_instance):
        class create_apply:
            def __init__(self):
                self.hogehoge = 'value1'
        c = create_apply()
        a = SyncSharedObject(updated_member = [],
                             created_member = [SyncInstanceMember(instance_id=id(c), member_name='hogehoge2', value={'type': 'pointer', 'value': 1234})],
                             deleted_member = [],
                             created_instance = [SyncInstance(instance_id=1234, value={'__type__': 'object', 'hogehoge3':{'type': 'pointer', 'value': 5678}}), SyncInstance(instance_id=5678, value={'__type__': 'object', 'boohoo':{'type': 'native', 'value': 'value2'}})],
                             deleted_instance = [])
        apply_unsirial(c, a)
        assert c.hogehoge == 'value1'
        assert [d for d in dir(c.hogehoge2) if not d.startswith('__')] == ['hogehoge3']
        assert c.hogehoge2.hogehoge3.boohoo == 'value2'
        assert [d for d in dir(c.hogehoge2.hogehoge3) if not d.startswith('__')] == ['boohoo']

    def test__createinstanceclass_apply(self, init_instance):
        class create_apply:
            def __init__(self):
                self.hogehoge = 'value1'
        c = create_apply()
        a = SyncSharedObject(updated_member = [],
                             created_member = [SyncInstanceMember(instance_id=id(c), member_name='hogehoge2', value={'type': 'pointer', 'value': 1234})],
                             deleted_member = [],
                             created_instance = [SyncInstance(instance_id=1234, value={'__type__': 'object'})],
                             deleted_instance = [])
        apply_unsirial(c, a)
        assert c.hogehoge == 'value1'
        assert [d for d in dir(c.hogehoge2) if not d.startswith('__')] == []

    def test__createinstancemember_apply(self, init_instance):
        class create_apply:
            def __init__(self):
                self.hogehoge = 'value1'
        c = create_apply()
        a = SyncSharedObject(updated_member = [],
                             created_member = [SyncInstanceMember(instance_id=id(c), member_name='hogehoge2', value={'type': 'pointer', 'value': 1234})],
                             deleted_member = [],
                             created_instance = [SyncInstance(instance_id=1234, value={'__type__': 'object', 'boohoo':{'type': 'native', 'value': 'value2'}})],
                             deleted_instance = [])
        apply_unsirial(c, a)
        assert c.hogehoge == 'value1'
        assert [d for d in dir(c.hogehoge2) if not d.startswith('__')] == ['boohoo']
        assert c.hogehoge2.boohoo == 'value2'

    def test__deleteinstance_apply(self, init_instance):
        clz1 = types.new_class(f'test__delete_apply_1', (object,))
        clz2 = types.new_class(f'test__delete_apply_2', (object,))
        c1 = clz1()
        c2 = clz1()
        c1.__setattr__('hogehoge','value1')
        c1.__setattr__('hogehoge2',c2)
        c2.__setattr__('boohoo','value2')
        a = SyncSharedObject(updated_member = [],
                             created_member = [],
                             deleted_member = [],
                             created_instance = [],
                             deleted_instance = [SyncInstance(instance_id=id(c2), value={'__type__': 'object', 'boohoo':{'type': 'native', 'value': 'value2'}})])
        apply_unsirial(c1, a)
        assert c1.hogehoge == 'value1'
        assert [d for d in dir(c1) if not d.startswith('__')] == ['hogehoge']

    def test__deleteinstanceclass_apply(self, init_instance):
        class delete_apply_1:
            def __init__(self, p):
                self.hogehoge = 'value1'
                self.hogehoge2 = p
        class delete_apply_2:
            def __init__(self):
                self.boohoo = 'value2'
        c2 = delete_apply_2()
        c1 = delete_apply_1(c2)
        a = SyncSharedObject(updated_member = [],
                             created_member = [],
                             deleted_member = [],
                             created_instance = [],
                             deleted_instance = [SyncInstance(instance_id=id(c2), value={'__type__': 'object', 'boohoo':{'type': 'native', 'value': 'value2'}})])
        apply_unsirial(c1, a)
        assert c1.hogehoge == 'value1'
        assert [d for d in dir(c1) if not d.startswith('__')] == ['hogehoge']


class TestSimpleApplyDict:
    @pytest.fixture
    def init_instance(self):
        pass

    def test__update_dictapply(self, init_instance):
        c = {'hogehoge':'value1'}
        a = SyncSharedObject(updated_member = [SyncInstanceMember(instance_id=id(c), member_name={'type': 'native', 'value': 'hogehoge'}, value={'type': 'native', 'value': 'value2'})],
                             created_member = [],
                             deleted_member = [],
                             created_instance = [],
                             deleted_instance = [])
        apply_unsirial(c, a)
        assert c == {'hogehoge':'value2'}

    def test__create_dictapply(self, init_instance):
        c = {'hogehoge':'value1'}
        a = SyncSharedObject(updated_member = [],
                             created_member = [SyncInstanceMember(instance_id=id(c), member_name={'type': 'native', 'value': 'hogehoge2'}, value={'type': 'native', 'value': 'value2'})],
                             deleted_member = [],
                             created_instance = [],
                             deleted_instance = [])
        apply_unsirial(c, a)
        assert c == {'hogehoge':'value1','hogehoge2':'value2'}

    def test__remove_dictapply(self, init_instance):
        c = {'hogehoge':'value1','hogehoge2':'value2'}
        a = SyncSharedObject(updated_member = [],
                             created_member = [],
                             deleted_member = [SyncInstanceMember(instance_id=id(c), member_name={'type': 'native', 'value': 'hogehoge2'}, value={'type': 'native', 'value': 'value2'})],
                             created_instance = [],
                             deleted_instance = [])
        apply_unsirial(c, a)
        assert c == {'hogehoge':'value1'}

    def test__createinstance_dictapply(self, init_instance):
        c = {'hogehoge':'value1'}
        a = SyncSharedObject(updated_member = [],
                             created_member = [SyncInstanceMember(instance_id=id(c), member_name={'type': 'native', 'value': 'hogehoge2'}, value={'type': 'pointer', 'value': 1234})],
                             deleted_member = [],
                             created_instance = [SyncInstance(instance_id=1234, value={'__type__': 'object'})],
                             deleted_instance = [])
        apply_unsirial(c, a)
        assert c['hogehoge'] == 'value1'
        assert c['hogehoge2']
        assert [d for d in dir(c['hogehoge2']) if not d.startswith('__')] == []


class TestDiffApply:
    @pytest.fixture
    def init_instance(self):
        pass

    def test__update_apply(self, init_instance):
        clz = types.new_class(f'test__simple_apply', (object,))
        c = clz()
        c.__setattr__('hogehoge','value1')
        d1 = dumps(c, snippet_share_only=False)
        a = SyncSharedObject(updated_member = [SyncInstanceMember(instance_id=id(c), member_name='hogehoge', value={'type': 'native', 'value': 'value2'})],
                             created_member = [],
                             deleted_member = [],
                             created_instance = [],
                             deleted_instance = [])
        apply_unsirial(c, a)
        d2 = dumps(c, snippet_share_only=False)
        d = diff(d1, d2)
        old = id(c)
        c = clz()
        c.__setattr__('hogehoge','value1')
        apply_unsirial(c, d, idmap_target_object={id(c):old})
        assert c.hogehoge == 'value2'
        assert [d for d in dir(c) if not d.startswith('__')] == ['hogehoge']

    def test__update_class_apply(self, init_instance):
        class update_apply:
            def __init__(self):
                self.hogehoge = 'value1'
        c = update_apply()
        d1 = dumps(c, snippet_share_only=False)
        a = SyncSharedObject(updated_member = [SyncInstanceMember(instance_id=id(c), member_name='hogehoge', value={'type': 'native', 'value': 'value2'})],
                             created_member = [],
                             deleted_member = [],
                             created_instance = [],
                             deleted_instance = [])
        apply_unsirial(c, a)
        d2 = dumps(c, snippet_share_only=False)
        d = diff(d1, d2)
        old = id(c)
        c = update_apply()
        apply_unsirial(c, d, idmap_target_object={id(c):old})
        assert c.hogehoge == 'value2'
        assert [d for d in dir(c) if not d.startswith('__')] == ['hogehoge']

    def test__create_apply(self, init_instance):
        clz = types.new_class(f'test__create_apply', (object,))
        c = clz()
        c.__setattr__('hogehoge','value1')
        d1 = dumps(c, snippet_share_only=False)
        a = SyncSharedObject(updated_member = [],
                             created_member = [SyncInstanceMember(instance_id=id(c), member_name='hogehoge2', value={'type': 'native', 'value': 'value2'})],
                             deleted_member = [],
                             created_instance = [],
                             deleted_instance = [])
        apply_unsirial(c, a)
        d2 = dumps(c, snippet_share_only=False)
        d = diff(d1, d2)
        old = id(c)
        c = clz()
        c.__setattr__('hogehoge','value1')
        apply_unsirial(c, d, idmap_target_object={id(c):old})
        assert c.hogehoge == 'value1'
        assert c.hogehoge2 == 'value2'
        assert [d for d in dir(c) if not d.startswith('__')] == ['hogehoge','hogehoge2']

    def test__create_class_apply(self, init_instance):
        class create_apply:
            def __init__(self):
                self.hogehoge = 'value1'
        c = create_apply()
        d1 = dumps(c, snippet_share_only=False)
        a = SyncSharedObject(updated_member = [],
                             created_member = [SyncInstanceMember(instance_id=id(c), member_name='hogehoge2', value={'type': 'native', 'value': 'value2'})],
                             deleted_member = [],
                             created_instance = [],
                             deleted_instance = [])
        apply_unsirial(c, a)
        d2 = dumps(c, snippet_share_only=False)
        d = diff(d1, d2)
        old = id(c)
        c = create_apply()
        apply_unsirial(c, d, idmap_target_object={id(c):old})
        assert c.hogehoge == 'value1'
        assert c.hogehoge2 == 'value2'
        assert [d for d in dir(c) if not d.startswith('__')] == ['hogehoge','hogehoge2']

    def test__remove_apply(self, init_instance):
        clz = types.new_class(f'test__remove_apply', (object,))
        c = clz()
        c.__setattr__('hogehoge','value1')
        c.__setattr__('hogehoge2','value2')
        d1 = dumps(c, snippet_share_only=False)
        a = SyncSharedObject(updated_member = [],
                             created_member = [],
                             deleted_member = [SyncInstanceMember(instance_id=id(c), member_name='hogehoge2', value={'type': 'native', 'value': 'value2'})],
                             created_instance = [],
                             deleted_instance = [])
        apply_unsirial(c, a)
        d2 = dumps(c, snippet_share_only=False)
        d = diff(d1, d2)
        old = id(c)
        c = clz()
        c.__setattr__('hogehoge','value1')
        c.__setattr__('hogehoge2','value2')
        apply_unsirial(c, d, idmap_target_object={id(c):old})
        assert c.hogehoge == 'value1'
        try:
            print(c.hogehoge2)
            assert False
        except AttributeError:
            pass
        assert [d for d in dir(c) if not d.startswith('__')] == ['hogehoge']

    def test__remove_class_apply(self, init_instance):
        class remove_apply:
            def __init__(self):
                self.hogehoge = 'value1'
                self.hogehoge2 = 'value2'
        c = remove_apply()
        d1 = dumps(c, snippet_share_only=False)
        a = SyncSharedObject(updated_member = [],
                             created_member = [],
                             deleted_member = [SyncInstanceMember(instance_id=id(c), member_name='hogehoge2', value={'type': 'native', 'value': 'value2'})],
                             created_instance = [],
                             deleted_instance = [])
        apply_unsirial(c, a)
        d2 = dumps(c, snippet_share_only=False)
        d = diff(d1, d2)
        old = id(c)
        c = remove_apply()
        apply_unsirial(c, d, idmap_target_object={id(c):old})
        assert c.hogehoge == 'value1'
        try:
            print(c.hogehoge2)
            assert False
        except AttributeError:
            pass
        assert [d for d in dir(c) if not d.startswith('__')] == ['hogehoge']

    def test__createinstance_apply(self, init_instance):
        clz = types.new_class(f'test__create_apply', (object,))
        c = clz()
        c.__setattr__('hogehoge','value1')
        d1 = dumps(c, snippet_share_only=False)
        a = SyncSharedObject(updated_member = [],
                             created_member = [SyncInstanceMember(instance_id=id(c), member_name='hogehoge2', value={'type': 'pointer', 'value': 1234})],
                             deleted_member = [],
                             created_instance = [SyncInstance(instance_id=1234, value={'__type__': 'object'})],
                             deleted_instance = [])
        apply_unsirial(c, a)
        d2 = dumps(c, snippet_share_only=False)
        d = diff(d1, d2)
        old = id(c)
        c = clz()
        c.__setattr__('hogehoge','value1')
        apply_unsirial(c, d, idmap_target_object={id(c):old})
        assert c.hogehoge == 'value1'
        assert [d for d in dir(c.hogehoge2) if not d.startswith('__')] == []

    def test__createinstancemember_apply(self, init_instance):
        clz = types.new_class(f'test__create_apply_1', (object,))
        c = clz()
        c.__setattr__('hogehoge','value1')
        d1 = dumps(c, snippet_share_only=False)
        a = SyncSharedObject(updated_member = [],
                             created_member = [SyncInstanceMember(instance_id=id(c), member_name='hogehoge2', value={'type': 'pointer', 'value': 1234})],
                             deleted_member = [],
                             created_instance = [SyncInstance(instance_id=1234, value={'__type__': 'object', 'boohoo':{'type': 'native', 'value': 'value2'}})],
                             deleted_instance = [])
        apply_unsirial(c, a)
        d2 = dumps(c, snippet_share_only=False)
        d = diff(d1, d2)
        old = id(c)
        c = clz()
        c.__setattr__('hogehoge','value1')
        apply_unsirial(c, d, idmap_target_object={id(c):old})
        assert c.hogehoge == 'value1'
        assert [d for d in dir(c.hogehoge2) if not d.startswith('__')] == ['boohoo']
        assert c.hogehoge2.boohoo == 'value2'

    def test__createinstancepointer_apply(self, init_instance):
        clz = types.new_class(f'test__create_apply', (object,))
        c = clz()
        c.__setattr__('hogehoge','value1')
        d1 = dumps(c, snippet_share_only=False)
        a = SyncSharedObject(updated_member = [],
                             created_member = [SyncInstanceMember(instance_id=id(c), member_name='hogehoge2', value={'type': 'pointer', 'value': 1234})],
                             deleted_member = [],
                             created_instance = [SyncInstance(instance_id=1234, value={'__type__': 'object', 'hogehoge3':{'type': 'pointer', 'value': 5678}}), SyncInstance(instance_id=5678, value={'__type__': 'object', 'boohoo':{'type': 'native', 'value': 'value2'}})],
                             deleted_instance = [])
        apply_unsirial(c, a)
        d2 = dumps(c, snippet_share_only=False)
        d = diff(d1, d2)
        old = id(c)
        c = clz()
        c.__setattr__('hogehoge','value1')
        apply_unsirial(c, d, idmap_target_object={id(c):old})
        assert c.hogehoge == 'value1'
        assert [d for d in dir(c.hogehoge2) if not d.startswith('__')] == ['hogehoge3']
        assert c.hogehoge2.hogehoge3.boohoo == 'value2'
        assert [d for d in dir(c.hogehoge2.hogehoge3) if not d.startswith('__')] == ['boohoo']

    def test__createinstancepointerclass_apply(self, init_instance):
        class create_apply:
            def __init__(self):
                self.hogehoge = 'value1'
        c = create_apply()
        d1 = dumps(c, snippet_share_only=False)
        a = SyncSharedObject(updated_member = [],
                             created_member = [SyncInstanceMember(instance_id=id(c), member_name='hogehoge2', value={'type': 'pointer', 'value': 1234})],
                             deleted_member = [],
                             created_instance = [SyncInstance(instance_id=1234, value={'__type__': 'object', 'hogehoge3':{'type': 'pointer', 'value': 5678}}), SyncInstance(instance_id=5678, value={'__type__': 'object', 'boohoo':{'type': 'native', 'value': 'value2'}})],
                             deleted_instance = [])
        apply_unsirial(c, a)
        d2 = dumps(c, snippet_share_only=False)
        d = diff(d1, d2)
        old = id(c)
        c = create_apply()
        apply_unsirial(c, d, idmap_target_object={id(c):old})
        assert c.hogehoge == 'value1'
        assert [d for d in dir(c.hogehoge2) if not d.startswith('__')] == ['hogehoge3']
        assert c.hogehoge2.hogehoge3.boohoo == 'value2'
        assert [d for d in dir(c.hogehoge2.hogehoge3) if not d.startswith('__')] == ['boohoo']

    def test__createinstanceclass_apply(self, init_instance):
        class create_apply:
            def __init__(self):
                self.hogehoge = 'value1'
        c = create_apply()
        d1 = dumps(c, snippet_share_only=False)
        a = SyncSharedObject(updated_member = [],
                             created_member = [SyncInstanceMember(instance_id=id(c), member_name='hogehoge2', value={'type': 'pointer', 'value': 1234})],
                             deleted_member = [],
                             created_instance = [SyncInstance(instance_id=1234, value={'__type__': 'object'})],
                             deleted_instance = [])
        apply_unsirial(c, a)
        d2 = dumps(c, snippet_share_only=False)
        d = diff(d1, d2)
        old = id(c)
        c = create_apply()
        apply_unsirial(c, d, idmap_target_object={id(c):old})
        assert c.hogehoge == 'value1'
        assert [d for d in dir(c.hogehoge2) if not d.startswith('__')] == []

    def test__createinstancemember_apply(self, init_instance):
        class create_apply:
            def __init__(self):
                self.hogehoge = 'value1'
        c = create_apply()
        d1 = dumps(c, snippet_share_only=False)
        a = SyncSharedObject(updated_member = [],
                             created_member = [SyncInstanceMember(instance_id=id(c), member_name='hogehoge2', value={'type': 'pointer', 'value': 1234})],
                             deleted_member = [],
                             created_instance = [SyncInstance(instance_id=1234, value={'__type__': 'object', 'boohoo':{'type': 'native', 'value': 'value2'}})],
                             deleted_instance = [])
        apply_unsirial(c, a)
        d2 = dumps(c, snippet_share_only=False)
        d = diff(d1, d2)
        old = id(c)
        c = create_apply()
        apply_unsirial(c, d, idmap_target_object={id(c):old})
        assert c.hogehoge == 'value1'
        assert [d for d in dir(c.hogehoge2) if not d.startswith('__')] == ['boohoo']
        assert c.hogehoge2.boohoo == 'value2'

    def test__deleteinstance_apply(self, init_instance):
        clz1 = types.new_class(f'test__delete_apply_1', (object,))
        clz2 = types.new_class(f'test__delete_apply_2', (object,))
        c1 = clz1()
        c2 = clz1()
        c1.__setattr__('hogehoge','value1')
        c1.__setattr__('hogehoge2',c2)
        c2.__setattr__('boohoo','value2')
        d1 = dumps(c1, snippet_share_only=False)
        a = SyncSharedObject(updated_member = [],
                             created_member = [],
                             deleted_member = [],
                             created_instance = [],
                             deleted_instance = [SyncInstance(instance_id=id(c2), value={'__type__': 'object', 'boohoo':{'type': 'native', 'value': 'value2'}})])
        apply_unsirial(c1, a)
        d2 = dumps(c1, snippet_share_only=False)
        d = diff(d1, d2)
        old1 = id(c1)
        old2 = id(c2)
        c1 = clz1()
        c2 = clz1()
        c1.__setattr__('hogehoge','value1')
        c1.__setattr__('hogehoge2',c2)
        c2.__setattr__('boohoo','value2')
        apply_unsirial(c1, d, idmap_target_object={id(c1):old1,id(c2):old2})
        assert c1.hogehoge == 'value1'
        assert [d for d in dir(c1) if not d.startswith('__')] == ['hogehoge']

    def test__deleteinstanceclass_apply(self, init_instance):
        class delete_apply_1:
            def __init__(self, p):
                self.hogehoge = 'value1'
                self.hogehoge2 = p
        class delete_apply_2:
            def __init__(self):
                self.boohoo = 'value2'
        c2 = delete_apply_2()
        c1 = delete_apply_1(c2)
        d1 = dumps(c1, snippet_share_only=False)
        a = SyncSharedObject(updated_member = [],
                             created_member = [],
                             deleted_member = [],
                             created_instance = [],
                             deleted_instance = [SyncInstance(instance_id=id(c2), value={'__type__': 'object', 'boohoo':{'type': 'native', 'value': 'value2'}})])
        apply_unsirial(c1, a)
        d2 = dumps(c1, snippet_share_only=False)
        d = diff(d1, d2)
        old1 = id(c1)
        old2 = id(c2)
        c2 = delete_apply_2()
        c1 = delete_apply_1(c2)
        apply_unsirial(c1, d, idmap_target_object={id(c1):old1,id(c2):old2})
        assert c1.hogehoge == 'value1'
        assert [d for d in dir(c1) if not d.startswith('__')] == ['hogehoge']
