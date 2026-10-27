"""Profiled source inventory and native registration of unindexed scene speech."""
import struct
from native import DEPLOY, Reader, UnityFile, catalog, pack_string, read_source, rebuild, require, sha
from storage import encoded


def paths(shape):
    return [DEPLOY, *shape.get('scene_resources', [])]


def fingerprint(data):
    return sha(data) if isinstance(data, bytes) else sha(encoded({k: sha(v) for k, v in sorted(data.items())}))


def blobs(data):
    return {DEPLOY: data} if isinstance(data, bytes) else data


def actions(data):
    unity = UnityFile(data)
    result = []
    for obj in unity.objects:
        if obj['type'][0] != 114:
            continue
        raw = unity.raw(obj)
        try:
            name, span = Reader(raw, 28).string()
        except (ValueError, UnicodeError):
            continue
        if not (name == 'ActionSpeech' or name.startswith('ActionSpeech(Clone)')):
            continue
        candidates = []
        # The two observed Action-base serializations differ in their output
        # socket envelope. Both must satisfy the entire derived speech layout.
        for delta in (112, 156):
            try:
                start = span[1] + delta
                r = Reader(raw, start)
                text, text_span = r.string()
                require(not any(ord(c) < 32 and c not in '\r\n\t' for c in text),
                        'Not a speech message')
                id_offset = r.pos
                line_id = r.i()
                require(line_id >= -1, 'Invalid speech line ID')
                require(r.i() == 0, 'Multiline action IDs require adapter review')
                require(r.i() in (0, 1) and r.i() in (0, 1), 'Invalid speech booleans')
                r.take(24)  # head/mouth AnimationClip references, never modified
                require(r.i() in (0, 1), 'Invalid head animation flag')
                r.string(); r.i()
                require(r.i() in (0, 1), 'Invalid mouth animation flag')
                r.string(); r.i(); r.take(4)
                require(r.pos == len(raw), 'Unexpected ActionSpeech tail')
                constant_id, param, message_param, player, player_id, speaker_file, speaker_path = struct.unpack_from('<iiiiiiq', raw, start - 32)
                require(player in (0, 1) and param >= -1 and message_param >= -1 and player_id >= -1,
                        'Unknown ActionSpeech parameter fields')
                candidates.append({'object': obj, 'raw': raw, 'name': name,
                    'text': text, 'text_span': text_span, 'line_id': line_id,
                    'id_offset': id_offset, 'is_player': bool(player),
                    'speaker_ref': [speaker_file, speaker_path],
                    'message_parameter_id': message_param, 'parameter_id': param,
                    'constant_id': constant_id, 'player_id': player_id, 'layout_delta': delta})
            except (ValueError, UnicodeError, struct.error):
                continue
        require(len(candidates) == 1, f'Unknown/ambiguous ActionSpeech layout at PathID {obj["id"]}')
        result.append(candidates[0])
    return unity, result


def source_catalog(data, shape):
    all_blobs = blobs(data)
    require(set(all_blobs) == set(paths(shape)), 'Incomplete/unknown managed source inventory')
    central = catalog(all_blobs[DEPLOY], shape)
    by_id = {r['key']: r for r in central}
    _, resource_actions = actions(all_blobs[DEPLOY])
    for action in resource_actions:
        require(action['line_id'] in by_id and by_id[action['line_id']]['EN'] == action['text'],
                'Unregistered/changed resources ActionSpeech requires adapter review')
    extra = []
    for rel in shape.get('scene_resources', []):
        _, found = actions(all_blobs[rel])
        def speaker_key(a):
            return (a['is_player'], a['player_id'], tuple(a['speaker_ref']), a['constant_id'], a['parameter_id'])
        identities = {}
        for action in found:
            if action['line_id'] in by_id:
                require(by_id[action['line_id']]['EN'] == action['text'], 'Registered source text differs')
                owner = by_id[action['line_id']]['context']['owner']
                if owner:
                    identities.setdefault(speaker_key(action), {}).setdefault(owner, []).append(action['line_id'])
        for a in found:
            if not a['text']:
                require(a['line_id'] == -1, 'Unexpected empty registered message')
                continue
            if a['line_id'] >= 0:
                require(a['line_id'] in by_id and by_id[a['line_id']]['EN'] == a['text'],
                        f'Scene speech ID/text mismatch: {rel} PathID {a["object"]["id"]}')
                continue
            require(a['message_parameter_id'] == -1, 'Dynamic unindexed speech requires manual mapping review')
            pid = a['object']['id']
            context = {'text_type': 'Speech', 'native_translation_id': -1,
                    'owner': 'unknown', 'scene': rel, 'object_name': a['name'],
                    'is_player': a['is_player'], 'speaker_reference': a['speaker_ref'],
                    'speaker_parameter_id': a['parameter_id'], 'player_id': a['player_id'],
                    'speaker_gender': 'unknown', 'addressee': 'unknown', 'referent_gender': 'unknown',
                    'identity_evidence': 'Unity PathID plus native field; IDs may change after scene reserialization',
                    'registration': 'Build appends a native SpeechLine and replaces only this action translation ID'}
            linked = identities.get(speaker_key(a), {})
            if len(linked) == 1 and a['parameter_id'] == -1:
                owner, witnesses = next(iter(linked.items()))
                witness = min(witnesses)
                known = by_id[witness]['context']
                context.update({'owner': owner, 'speaker': owner,
                    'speaker_evidence': {'method': 'same native speaker/player/constant references in this scene',
                                         'witness_line_id': witness},
                    'speaker_gender': known['speaker_gender']})
                if 'gender_evidence' in known:
                    context['gender_evidence'] = known['gender_evidence']
            extra.append({'id': f'{rel}#PathID:{pid}:ActionSpeech.messageText',
                'key': pid, 'row': len(extra), 'source_file': rel, 'EN': a['text'], 'FR': '', 'PTBR': '',
                'context': context})
    return central + extra


def build_sources(data, shape, records, register=True):
    all_blobs = blobs(data)
    native_records = [r for r in records if r['source_file'] == DEPLOY]
    extra = sorted((r for r in records if r['source_file'] != DEPLOY), key=lambda r: r['id'])
    _, _, table = read_source(all_blobs[DEPLOY], shape)
    next_id = max(r['line_id'] for r in table.rows) + 1
    require(next_id + len(extra) < 2**31, 'Translation ID space exhausted')
    additions, assigned = [], {}
    for n, r in enumerate(extra):
        line_id = next_id + n
        assigned[r['id']] = line_id
        additions.append({'line_id': line_id, 'player': r['context']['is_player'],
            'scene': r['source_file'], 'owner': r['context']['owner'] if r['context']['owner'] != 'unknown' else '', 'EN': r['EN'],
            'description': r['id'], 'PTBR': r['PTBR']})
    out = {DEPLOY: rebuild(all_blobs[DEPLOY], shape,
        {r['key']: r['PTBR'] for r in native_records}, register, additions if register else ())}
    for rel in shape.get('scene_resources', []):
        unity, found = actions(all_blobs[rel])
        replacements = {}
        for a in found:
            if a['line_id'] != -1 or not a['text']:
                continue
            key = f'{rel}#PathID:{a["object"]["id"]}:ActionSpeech.messageText'
            require(key in assigned, 'Missing unindexed action record')
            if register:
                patched = bytearray(a['raw'])
                struct.pack_into('<i', patched, a['id_offset'], assigned[key])
                replacements[a['object']['id']] = bytes(patched)
        rewritten = unity.rewrite(replacements)
        if replacements or not register:
            out[rel] = rewritten
        _, checked = actions(rewritten)
        for before, after in zip(found, checked):
            require(before['text'] == after['text'] and before['speaker_ref'] == after['speaker_ref'],
                    'Scene message/speaker changed during ID registration')
            key = f'{rel}#PathID:{before["object"]["id"]}:ActionSpeech.messageText'
            expected = assigned[key] if before['line_id'] == -1 and before['text'] and register else before['line_id']
            require(after['line_id'] == expected, 'Scene registration ID differs')
    return out
