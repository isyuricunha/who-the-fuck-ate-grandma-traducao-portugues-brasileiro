"""Strict, pre-authored visual overrides; runtime remains stdlib-only.

Each source, object and byte range is hash-bound to this exact game build.
No installed file is read or written by the package build.
"""
import json
import struct
from pathlib import Path
from native import UnityFile, require, sha
from storage import safe

PROFILE = 'translation-work/visuals/profile.json'


def profile(root):
    path = Path(root) / PROFILE
    if not path.exists(): return None
    data = json.loads(path.read_text('utf-8'))
    require(data['schema'] == 1, 'Unknown visual profile')
    return data


def inputs(root):
    p = profile(root)
    return [] if p is None else [PROFILE, *p['inputs']]


def targets(root):
    p = profile(root)
    return set() if p is None else set(p['files'])


def validate_inputs(root):
    p = profile(root)
    if p is None: return
    for path, expected in p['inputs'].items():
        require(sha(safe(root,path).read_bytes())==expected,'Visual input changed: '+path)


def append_objects(data, additions):
    if not additions: return data
    u = UnityFile(data)
    require(len({a['id'] for a in additions}) == len(additions), 'Duplicate appended object')
    require(not {a['id'] for a in additions} & {o['id'] for o in u.objects}, 'Appended ID collision')
    first = u.objects[0]['address']
    possible = [off for off in range(first-7,first-3) if struct.unpack_from('<i',data,off)[0] == len(u.objects)]
    require(len(possible) == 1, 'Unknown Unity object-count location')
    count_offset = possible[0]
    table_end = u.objects[-1]['address'] + 24
    require(all(b['address']-a['address'] == 24 for a,b in zip(u.objects,u.objects[1:])),
            'Unknown object-table stride')
    payload = bytearray(data[u.start:]); entries = bytearray()
    for a in additions:
        require(0 <= a['type_index'] < len(u.types), 'Unknown appended type')
        payload.extend(bytes(-len(payload) % 16))
        entries.extend(struct.pack('<qQIi',a['id'],len(payload),len(a['raw']),a['type_index']))
        payload.extend(a['raw'])
    metadata_end = 48+u.metadata_size
    require(not any(data[metadata_end:u.start]), 'Unexpected metadata padding')
    head = bytearray(data[:table_end] + entries + data[table_end:metadata_end])
    struct.pack_into('<i',head,count_offset,len(u.objects)+len(additions))
    start = max(u.start, (len(head)+15)//16*16)
    head.extend(bytes(start-len(head))); result = head+payload
    struct.pack_into('>I',result,20,u.metadata_size+len(entries))
    struct.pack_into('>Q',result,24,len(result)); struct.pack_into('>Q',result,32,start)
    reopened = UnityFile(bytes(result)); old = {o['id']:o for o in u.objects}
    new = {a['id']:a['raw'] for a in additions}
    require(len(reopened.objects)==len(old)+len(new), 'Appended inventory mismatch')
    for o in reopened.objects:
        expected = new[o['id']] if o['id'] in new else u.raw(old[o['id']])
        require(reopened.raw(o)==expected,'Payload changed during object append')
    return bytes(result)


def apply(root, outputs):
    p = profile(root)
    if p is None: return outputs
    validate_inputs(root)
    result = dict(outputs)
    for rel, spec in p['files'].items():
        original = safe(root,spec['source']).read_bytes()
        require(sha(original)==spec['source_sha256'],'Unknown visual source: '+rel)
        base = result.get(rel,original)
        if spec['kind']=='unity':
            before = UnityFile(original); after = UnityFile(base)
            originals = {o['id']:o for o in before.objects}; current = {o['id']:o for o in after.objects}
            replacements = {}
            for patch in spec['objects']:
                pid=patch['id']; require(pid in originals and pid in current,'Missing visual object')
                old=before.raw(originals[pid])
                require(sha(old)==patch['before_sha256'] and after.raw(current[pid])==old,
                        'Visual target changed upstream: '+str(pid))
                require(list(current[pid]['type'])==patch['type'],'Visual object type changed')
                replacements[pid]=safe(root,patch['payload']).read_bytes()
                require(sha(replacements[pid])==patch['after_sha256'],'Visual payload changed')
            base=after.rewrite(replacements)
            additions=[{'id':a['id'],'type_index':a['type_index'],
                        'raw':safe(root,a['payload']).read_bytes()} for a in spec.get('additions',[])]
            base=append_objects(base,additions)
        elif spec['kind']=='binary':
            require(base==original,'Binary visual source changed upstream')
            b=bytearray(base)
            for patch in spec['ranges']:
                off=patch['offset']; old=bytes.fromhex(patch['before']); new=bytes.fromhex(patch['after'])
                require(len(old)==len(new) and b[off:off+len(old)]==old,'Native selector signature changed')
                b[off:off+len(old)]=new
            base=bytes(b)
        else: raise ValueError('Unknown visual patch kind')
        result[rel]=base
    return result
