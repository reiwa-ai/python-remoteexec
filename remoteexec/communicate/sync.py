from typing import List, Dict, Tuple, Union, Callable, Optional
import inspect
import json
import types

from .serializer import __snippet_share__, dumps, loads

class SyncInstance:
    def __init__(self,
                 instance_id: int,
                 value: object):
        self.instance_id = int(instance_id)
        self.value = value

    def __str__(self):
        return f'SyncInstance(instance_id={self.instance_id},value={self.value})'

class SyncInstanceMember:
    def __init__(self,
                 instance_id: int,
                 member_name: str,
                 value: object):
        self.instance_id = int(instance_id)
        self.member_name = member_name
        self.value = value

    def __str__(self):
        return f'SyncInstanceMember(instance_id={self.instance_id},member_name={self.member_name},value={self.value})'

class SyncSharedObject:
    def __init__(self,
                 updated_member: List[SyncInstanceMember],
                 created_member: List[SyncInstanceMember],
                 deleted_member: List[SyncInstanceMember],
                 created_instance: List[SyncInstance],
                 deleted_instance: List[SyncInstance],
                 ):
        self.updated_member = updated_member
        self.created_member = created_member
        self.deleted_member = deleted_member
        self.created_instance = created_instance
        self.deleted_instance = deleted_instance
    
    def unserialized(serialized):
        data = json.loads(serialized)
        updated_member = [SyncInstanceMember(m["instance_id"], m["member_name"], m["value"]) for m in data["updated_member"]]
        created_member = [SyncInstanceMember(m["instance_id"], m["member_name"], m["value"]) for m in data["created_member"]]
        deleted_member = [SyncInstanceMember(m["instance_id"], m["member_name"], m["value"]) for m in data["deleted_member"]]
        created_instance = [SyncInstance(m["instance_id"], m["value"]) for m in data["created_instance"]]
        deleted_instance = [SyncInstance(m["instance_id"], m["value"]) for m in data["deleted_instance"]]
        return SyncSharedObject(updated_member = updated_member,
                                created_member = created_member,
                                deleted_member = deleted_member,
                                created_instance = created_instance,
                                deleted_instance = deleted_instance)
    
    def serialize(self):
        # valueがシリアライズ済み文字列のため__type__が含まれるためdictなので、dumpsで二重シリアライズできない
        data = {"updated_member":[{"instance_id":m.instance_id, "member_name":m.member_name, "value":m.value} for m in self.updated_member], 
                "created_member":[{"instance_id":m.instance_id, "member_name":m.member_name, "value":m.value} for m in self.created_member], 
                "deleted_member":[{"instance_id":m.instance_id, "member_name":m.member_name, "value":m.value} for m in self.deleted_member], 
                "created_instance":[{"instance_id":m.instance_id, "value":m.value} for m in self.created_instance], 
                "deleted_instance":[{"instance_id":m.instance_id, "value":m.value} for m in self.deleted_instance]}
        return json.dumps(data)

    def __str__(self):
        return 'SyncSharedObject.updated_member - ' + str([str(m) for m in self.updated_member]) + '\n' +\
               'SyncSharedObject.created_member - ' + str([str(m) for m in self.created_member]) + '\n' +\
               'SyncSharedObject.deleted_member - ' + str([str(m) for m in self.deleted_member]) + '\n' +\
               'SyncSharedObject.created_instance - ' + str([str(m) for m in self.created_instance]) + '\n' +\
               'SyncSharedObject.deleted_instance - ' + str([str(m) for m in self.deleted_instance])
    
def diff(before_shared_object_serial:object, updated_shared_object_serial:object) -> SyncSharedObject:
    before_instance = before_shared_object_serial['instance']
    updated_instance = updated_shared_object_serial['instance']

    updated_member = []
    created_member = []
    deleted_member = []
    created_instance = []
    deleted_instance = []

    for cur_instance_id, cur_instance_value in before_instance.items():
        if cur_instance_id not in updated_instance:
            deleted_instance.append(SyncInstance(cur_instance_id, cur_instance_value))
        elif cur_instance_value != updated_instance[cur_instance_id]:
            if cur_instance_value['__type__'] == 'dict':
                for cur_member_name, cur_member_value in zip(cur_instance_value['keys'], cur_instance_value['values']):
                    if cur_member_name not in updated_instance[cur_instance_id]['keys']:
                        deleted_member.append(SyncInstanceMember(cur_instance_id, cur_member_name, cur_member_value))
                    else:
                        cur_member_value_index = -1
                        for index in range(len(updated_instance[cur_instance_id]['values'])):
                            if updated_instance[cur_instance_id]['keys'][index] == cur_member_name:
                                cur_member_value_index = index
                                break
                        if cur_member_value_index >= 0:
                            if cur_member_value != updated_instance[cur_instance_id]['values'][cur_member_value_index]:
                                updated_member.append(SyncInstanceMember(cur_instance_id, cur_member_name, updated_instance[cur_instance_id]['values'][cur_member_value_index]))
                for upd_member_name, upd_member_value in zip(updated_instance[cur_instance_id]['keys'], updated_instance[cur_instance_id]['values']):
                    if upd_member_name not in cur_instance_value['keys']:
                        created_member.append(SyncInstanceMember(cur_instance_id, upd_member_name, upd_member_value))
            else:
                for cur_member_name, cur_member_value in cur_instance_value.items():
                    if cur_member_name not in updated_instance[cur_instance_id]:
                        deleted_member.append(SyncInstanceMember(cur_instance_id, cur_member_name, cur_member_value))
                    elif cur_member_value != updated_instance[cur_instance_id][cur_member_name]:
                        updated_member.append(SyncInstanceMember(cur_instance_id, cur_member_name, updated_instance[cur_instance_id][cur_member_name]))
                for upd_member_name, upd_member_value in updated_instance[cur_instance_id].items():
                    if upd_member_name not in cur_instance_value:
                        created_member.append(SyncInstanceMember(cur_instance_id, upd_member_name, upd_member_value))
    for upd_instance_id, upd_instance_value in updated_instance.items():
        if upd_instance_id not in before_instance:
            created_instance.append(SyncInstance(upd_instance_id, upd_instance_value))

    return SyncSharedObject(updated_member = updated_member,
                            created_member = created_member,
                            deleted_member = deleted_member,
                            created_instance = created_instance,
                            deleted_instance = deleted_instance)

def marge(prioritized_object:SyncSharedObject, unprioritized_object:SyncSharedObject) -> SyncSharedObject:
    dest = SyncSharedObject(updated_member = [c for c in prioritized_object.updated_member],
                            created_member = [c for c in prioritized_object.created_member],
                            deleted_member = [c for c in prioritized_object.deleted_member],
                            created_instance = [c for c in prioritized_object.created_instance],
                            deleted_instance = [c for c in prioritized_object.deleted_instance])
    toadd_updated_member, toadd_created_member = [], []
    for upd_member in unprioritized_object.updated_member:
        has_same = False
        for dst_member in dest.updated_member:
            if dst_member.instance_id == upd_member.instance_id and dst_member.member_name == upd_member.member_name:
                has_same = True
                break
        if not has_same:
            toadd_updated_member.append(upd_member)
    
    for upd_member in unprioritized_object.created_member:
        has_same = False
        for dst_member in dest.created_member:
            if dst_member.instance_id == upd_member.instance_id and dst_member.member_name == upd_member.member_name:
                has_same = True
                break
        if not has_same:
            toadd_created_member.append(upd_member)

    for del_member in dest.deleted_member:
        todel = []
        for instance in [toadd_updated_member, toadd_created_member]:
            for idx, dst_member in enumerate(instance):
                if dst_member.instance_id == del_member.instance_id and dst_member.member_name == del_member.member_name:
                    todel.append((instance, idx))
        for instance, idx in todel[::-1]:
            del instance[idx]
            
    for upd_member in unprioritized_object.deleted_member:
        has_same, has_same_nodelete = False, False
        for dst_member in dest.deleted_member:
            if dst_member.instance_id == upd_member.instance_id and dst_member.member_name == upd_member.member_name:
                has_same = True
                break
        for instance in [dest.updated_member, dest.created_member]:
            for dst_member in instance:
                if dst_member.instance_id == upd_member.instance_id and dst_member.member_name == upd_member.member_name:
                    has_same_nodelete = True
                    break
            if has_same_nodelete:
                break
        if (not has_same) and (not has_same_nodelete):
            dest.deleted_member.append(upd_member)
        elif has_same:
            todel = []
            for instance in [toadd_updated_member, toadd_created_member]:
                for idx, dst_member in enumerate(instance):
                    if dst_member.instance_id == upd_member.instance_id and dst_member.member_name == upd_member.member_name:
                        todel.append((instance, idx))
            for instance, idx in todel[::-1]:
                del instance[idx]

    for upd in toadd_updated_member:
        dest.updated_member.append(upd)
    for upd in toadd_created_member:
        dest.created_member.append(upd)

    for upd_instance in unprioritized_object.created_instance:
        has_same = False
        for dst_instance in dest.created_instance:
            if dst_instance.instance_id == upd_instance.instance_id:
                has_same = True
                break
        if not has_same:
            dest.created_instance.append(upd_instance)
    for upd_instance in unprioritized_object.deleted_instance:
        has_same = False
        for instance in [dest.created_instance, dest.deleted_instance]:
            for dst_instance in instance:
                if dst_instance.instance_id == upd_instance.instance_id:
                    has_same = True
                    break
            if has_same:
                break
        if not has_same:
            dest.deleted_instance.append(upd_instance)
    
    return dest

class ApplyInstance:
    def __init__(self, obj:object, parent:object, nameofparent:str):
        self.obj = obj
        self.parent = parent
        self.nameofparent = nameofparent

def apply_unsirial(target_object:object, sync_object:object, idmap_target_object:Optional[dict[int,int]]=None):

    def _id(obj):
        if idmap_target_object is not None and id(obj) in idmap_target_object:
            return int(idmap_target_object[id(obj)])
        return id(obj)

    def _listup_instance(_target_object:object):
        _out_instance = {}
        def _list(obj, parent, nameofparent, depth):
            d, e, f = None, None, None
            if _id(obj) not in _out_instance:
                if obj is None or isinstance(obj, int) or isinstance(obj, float) or isinstance(obj, str):
                    pass
                elif isinstance(obj, list) or isinstance(obj, tuple) or isinstance(obj, set):
                    d = {str(key):value for key,value in enumerate(obj)}
                elif isinstance(obj, dict):
                    d = None
                    e = obj
                elif hasattr(obj, '__dict__'):
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
                if d is not None:
                    if _id(obj) not in _out_instance:
                        _out_instance[_id(obj)] = []
                    _out_instance[_id(obj)].append(ApplyInstance(obj, parent, nameofparent))
                    for key,value in d.items():
                        _list(obj=value, parent=obj, nameofparent=key, depth=depth+1)
                elif e is not None:
                    if _id(obj) not in _out_instance:
                        _out_instance[_id(obj)] = []
                    _out_instance[_id(obj)].append(ApplyInstance(obj, parent, nameofparent))
                    for key,value in e.items():
                        _list(obj=key, parent=obj, nameofparent=key, depth=depth+1) # to tuple key
                        _list(obj=value, parent=obj, nameofparent=key, depth=depth+1)
        _list(obj=_target_object, parent=None, nameofparent=None, depth=0)
        return _out_instance

    out_instance = _listup_instance(target_object)
    
    for deleted_instance in sync_object.deleted_instance:
        if deleted_instance.instance_id in out_instance:
            for real_instance in out_instance[deleted_instance.instance_id]:
                if real_instance.parent is not None and hasattr(real_instance.parent, real_instance.nameofparent):
                    delattr(real_instance.parent, real_instance.nameofparent)

    for deleted_member in sync_object.deleted_member:
        if deleted_member.instance_id in out_instance:
            for real_instance in out_instance[deleted_member.instance_id]:
                if type(real_instance.obj) is dict:
                    if type(deleted_member.member_name) is dict:
                        if deleted_member.member_name['type'] == 'native':
                            del real_instance.obj[deleted_member.member_name['value']]
                        elif deleted_member.member_name['type'] == 'pointer':
                            if deleted_member.member_name['value'] in out_instance:
                                if out_instance[deleted_member.member_name['value']].obj in real_instance.obj:
                                    del real_instance.obj[out_instance[deleted_member.member_name['value']].obj]
                    elif deleted_member.member_name in real_instance.obj:
                        del real_instance.obj[deleted_member.member_name]
                elif type(real_instance.obj) is list:
                    if int(deleted_member.member_name) < len(real_instance.obj):
                        real_instance.obj[int(deleted_member.member_name)] = None
                elif type(real_instance.obj) is set:
                    real_instance.obj.discard(deleted_member.member_name)
                elif real_instance.obj is not None:
                    if hasattr(real_instance.obj, deleted_member.member_name):
                        delattr(real_instance.obj, deleted_member.member_name)

    new_instance = {}
    new_instance_serial_instance = {ci.instance_id:ci.value for ci in sync_object.created_instance}
    for old_instance_id in out_instance.keys():
        if old_instance_id not in new_instance_serial_instance:
            new_instance_serial_instance[old_instance_id] = {'__type__':'object'}
    for created_instance in sync_object.created_instance:
        new_instance_serial = {'object':created_instance.instance_id, 'instance':new_instance_serial_instance}
        new_instance_unserial = loads(new_instance_serial)
        new_instance[created_instance.instance_id] = ApplyInstance(new_instance_unserial, None, None)
        new_out_instance = _listup_instance(new_instance_unserial)
        for new_out_id in new_out_instance.keys():
            if new_out_id in out_instance:
                for new_out in new_out_instance[new_out_id]:
                    if new_out.parent is not None:
                        new_out.parent.__setattr__(new_out.nameofparent, out_instance[new_out_id][0].obj)

    for created_member in sync_object.created_member + sync_object.updated_member:
        update_instances = []
        if created_member.instance_id in out_instance:
            update_instances = out_instance[created_member.instance_id]
        elif created_member.instance_id in new_instance:
            update_instances = [new_instance[created_member.instance_id]]

        update_value = None
        if created_member.value['type'] == 'pointer':
            if created_member.value['value'] in out_instance:
                update_value = out_instance[created_member.value['value']][0].obj
            elif created_member.value['value'] in new_instance:
                update_value = new_instance[created_member.value['value']].obj
        elif created_member.value['type'] == 'native':
            update_value = created_member.value['value']

        for update_instance in update_instances:
            if update_instance is None or update_value is None:
                pass
            elif isinstance(update_instance.obj, list):
                position = int(created_member.member_name)
                if position >= len(update_instance.obj):
                    update_instance.obj.extend([None]*(1+position-len(update_instance.obj)))
                update_instance.obj[position] = update_value
            elif isinstance(update_instance.obj, set):
                try:
                    update_instance.obj.add(update_value)
                except Exception:
                    raise AttributeCannotUpdateError()
            elif isinstance(update_instance.obj, tuple):
                raise AttributeCannotUpdateError()
            elif isinstance(update_instance.obj, dict):
                if type(created_member.member_name) is dict:
                    if created_member.member_name['type'] == 'native':
                        update_instance.obj[created_member.member_name['value']] = update_value
                    elif created_member.member_name['type'] == 'pointer':
                        if created_member.member_name['value'] in out_instance:
                            if out_instance[created_member.member_name['value']].obj in update_instance.obj:
                                update_instance.obj[out_instance[created_member.member_name['value']].obj] = update_value
                        elif created_member.member_name['value'] in new_instance:
                            if new_instance[created_member.member_name['value']].obj in update_instance.obj:
                                update_instance.obj[new_instance[created_member.member_name['value']].obj] = update_value
                elif created_member.member_name in update_instance.obj:
                    update_instance.obj[created_member.member_name] = update_value
            elif type(update_instance.obj) is int or type(update_instance.obj) is float or type(update_instance.obj) is str:
                pass
            else:
                try:
                    update_instance.obj.__setattr__(created_member.member_name,update_value)
                except Exception:
                    raise AttributeCannotUpdateError()
