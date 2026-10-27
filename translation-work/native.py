"""Strict, dependency-free reader for this game's stripped Unity v22 profile.

No string guessing: object tables, aligned strings and SpeechLine records are
parsed structurally. Unknown profiles fail closed. Untouched object data stays
byte-identical, including textures, audio references and external stream paths.
"""
import base64
import collections
import hashlib
import struct

DEPLOY = 'Who the fuck ate grandma_Data/resources.assets'
KINDS = ['Speech', 'Hotspot', 'DialogueOption', 'InventoryItem', 'CursorIcon',
         'MenuElement', 'HotspotPrefix', 'JournalEntry', 'InventoryProperty',
         'Variable', 'Character', 'Document', 'Custom', 'Objective', 'Container']


class FormatError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise FormatError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pack_string(value):
    raw = value.encode('utf-8')
    require('\0' not in value, 'NUL in native string')
    return struct.pack('<I', len(raw)) + raw + bytes(-len(raw) % 4)


def replacement_suffix(shape):
    """Native Language.isDisabled: replace English in the enabled selector.

    Keep the original data for fallback, insert PT-BR first among translations,
    and preserve the French descriptor/text as the second active language.
    """
    old = base64.b64decode(shape['speech_suffix_b64'], validate=True)
    r = Reader(old, 16)
    require(r.i() == 2, 'Expected English/French language registry')
    descriptors = []
    for expected in ('English', 'Français'):
        start = r.pos
        name, _ = r.string()
        require(name == expected and r.i() == 0, 'Unexpected language/RTL profile')
        audio, _ = r.string(); lipsync, _ = r.string()
        require(not audio and not lipsync and r.i() == 0 and r.i() == 0,
                'Language dependency/fallback profile needs review')
        descriptors.append(old[start:r.pos])
    english = bytearray(descriptors[0])
    struct.pack_into('<i', english, len(english) - 4, 1)
    portuguese = pack_string('Português (Brasil)') + bytes(20)
    return old[:16] + struct.pack('<i', 3) + bytes(english) + portuguese + descriptors[1] + old[r.pos:]


class Reader:
    def __init__(self, data, pos=0):
        self.data, self.pos = data, pos

    def take(self, size):
        require(0 <= size <= len(self.data) - self.pos, 'Truncated native data')
        val = self.data[self.pos:self.pos + size]
        self.pos += size
        return val

    def i(self):
        return struct.unpack('<i', self.take(4))[0]

    def string(self):
        start = self.pos
        size = self.i()
        require(0 <= size <= 4 * 1024 * 1024, 'Invalid native string length')
        val = self.take(size).decode('utf-8', errors='strict')
        require('\0' not in val, 'NUL inside serialized string')
        require(not any(self.take(-self.pos % 4)), 'Nonzero string alignment')
        return val, (start, self.pos)


class UnityFile:
    def __init__(self, data):
        self.data = data
        require(len(data) >= 60, 'Truncated Unity header')
        require(struct.unpack_from('>I', data, 8)[0] == 22 and data[16] == 0,
                'Unsupported Unity version/endianness; profile needs review')
        self.metadata_size, size, self.start = struct.unpack_from('>IQQ', data, 20)
        require(size == len(data) and 48 + self.metadata_size <= self.start <= size,
                'Invalid Unity size/metadata bounds')
        p = data.find(b'\0', 48)
        require(48 < p < 100, 'Invalid Unity version string')
        self.version = data[48:p].decode('ascii')
        require(self.version == '6000.2.9f1', 'Unsupported engine build: ' + self.version)
        r = Reader(data, p + 1)
        require(r.i() == 19, 'Unsupported target platform (Windows player required)')
        require(r.take(1) == b'\0', 'Type-tree profile not supported')
        nt = r.i()
        require(0 < nt < 1000, 'Invalid type count')
        self.types = []
        for _ in range(nt):
            cid = r.i()
            r.take(1)
            script = struct.unpack('<h', r.take(2))[0]
            if cid == 114:
                r.take(16)
            r.take(16)
            self.types.append((cid, script))
        count = r.i()
        require(0 < count < 1000000, 'Invalid object count')
        self.objects = []
        ids = set()
        for _ in range(count):
            r.take(-r.pos % 4)
            addr = r.pos
            pid, offset, length, ti = struct.unpack('<qQIi', r.take(24))
            require(pid not in ids and 0 <= ti < nt, 'Duplicate object or bad type')
            require(offset + length <= len(data) - self.start, 'Object outside file')
            ids.add(pid)
            self.objects.append({'id': pid, 'offset': offset, 'size': length,
                                 'type': self.types[ti], 'address': addr})
        require(r.pos <= 48 + self.metadata_size, 'Object table outside metadata')
        last = 0
        for obj in sorted(self.objects, key=lambda x: x['offset']):
            require(obj['offset'] >= last, 'Overlapping Unity objects')
            last = obj['offset'] + obj['size']

    def raw(self, obj):
        p = self.start + obj['offset']
        return self.data[p:p + obj['size']]

    def named(self, name):
        found = []
        for obj in self.objects:
            if obj['type'][0] == 114:
                r = Reader(self.raw(obj), 28)
                try:
                    value, _ = r.string()
                except (ValueError, UnicodeError):
                    continue
                if value == name:
                    found.append(obj)
        require(len(found) == 1, 'Expected exactly one ' + name)
        return found[0]

    def rewrite(self, replacements):
        known = {o['id'] for o in self.objects}
        require(set(replacements) <= known, 'Unknown object replacement')
        changed = {o['id']: replacements[o['id']] for o in self.objects
                   if o['id'] in replacements and replacements[o['id']] != self.raw(o)}
        if not changed:
            return self.data
        head = bytearray(self.data[:self.start])
        chunks, end, length = [], self.start, 0
        for obj in sorted(self.objects, key=lambda x: x['offset']):
            begin = self.start + obj['offset']
            gap = self.data[end:begin]
            chunks.append(gap)
            length += len(gap)
            # Preserve the original object's alignment residue.
            pad = (obj['offset'] - length) % 16
            chunks.append(bytes(pad))
            length += pad
            raw = changed.get(obj['id'], self.raw(obj))
            struct.pack_into('<QI', head, obj['address'] + 8, length, len(raw))
            chunks.append(raw)
            length += len(raw)
            end = begin + obj['size']
        chunks.append(self.data[end:])
        result = head + b''.join(chunks)
        struct.pack_into('>Q', result, 24, len(result))
        reopened = UnityFile(bytes(result))
        previous = {o['id']: o for o in self.objects}
        for obj in reopened.objects:
            old = previous[obj['id']]
            require(reopened.raw(obj) == changed.get(obj['id'], self.raw(old)),
                    'Object payload changed unexpectedly')
        return bytes(result)


class SpeechTable:
    def __init__(self, data, shape):
        prefix = base64.b64decode(shape['speech_prefix_b64'], validate=True)
        require(data[:248] == prefix, 'SpeechManager header differs; adapter review required')
        self.data = data
        r = Reader(data, 248)
        count = r.i()
        require(0 < count < 100000, 'Invalid speech count')
        self.rows, ids = [], set()
        for order in range(count):
            start = r.pos
            player, line_id = r.i(), r.i()
            require(player in (0, 1) and 0 <= line_id and line_id not in ids,
                    'Invalid/duplicate native line ID')
            ids.add(line_id)
            scene, _ = r.string()
            owner, _ = r.string()
            en, _ = r.string()
            desc, _ = r.string()
            kind = r.i()
            translation_count = r.i()
            require(0 <= kind < len(KINDS) and translation_count == shape.get('translation_count', 1),
                    'Unknown text type or translation array layout')
            first, span = r.string()
            ptbr = None
            if translation_count == 2:
                ptbr = first
                fr, _ = r.string()
            else:
                fr = first
            tail = r.take(52)
            allowed = [bytes(52), bytes(32) + b'\xff' * 4 + bytes(16)]
            require(tail in allowed, 'Unknown SpeechLine companion fields')
            self.rows.append({'line_id': line_id, 'order': order, 'player': bool(player),
                              'scene': scene, 'owner': owner, 'EN': en, 'FR': fr,
                              'description': desc, 'kind': KINDS[kind],
                              'PTBR_runtime': ptbr,
                              'span': span, 'record_span': (start, r.pos)})
        self.end = r.pos
        expected_tail = base64.b64decode(shape['speech_suffix_b64'], validate=True)
        require(data[self.end:] == expected_tail, 'Language metadata differs; review required')

    def rewrite(self, texts, language=False, additions=()):
        ids = {x['line_id'] for x in self.rows}
        require(set(texts) <= ids, 'Unknown native ID')
        if language:
            require(set(texts) == ids, 'Every central text is required for English replacement')
            edits = []
            for row in self.rows:
                a, b = row['span']
                edits.extend([(a - 4, a, struct.pack('<i', 2)),
                              (a, b, pack_string(texts[row['line_id']]) + self.data[a:b])])
        else:
            edits = [(x['span'][0], x['span'][1], pack_string(texts[x['line_id']]))
                     for x in self.rows if x['line_id'] in texts]
        if additions:
            extra = bytearray()
            seen = set(ids)
            for row in additions:
                require(row['line_id'] not in seen and row['line_id'] >= 0, 'Duplicate appended translation ID')
                seen.add(row['line_id'])
                extra += struct.pack('<ii', int(row['player']), row['line_id'])
                for value in (row['scene'], row['owner'], row['EN'], row['description']):
                    extra += pack_string(value)
                extra += struct.pack('<ii', 0, 2) + pack_string(row['PTBR']) + pack_string(row.get('FR', row['EN'])) + bytes(52)
            edits.append((self.end, self.end, bytes(extra)))
            edits.append((248, 252, struct.pack('<i', len(self.rows) + len(additions))))
        if language:
            shape = {'speech_suffix_b64': base64.b64encode(self.data[self.end:]).decode()}
            edits.append((self.end, len(self.data), replacement_suffix(shape)))
        result = bytearray(self.data)
        for a, b, raw in sorted(edits, reverse=True):
            result[a:b] = raw
        return bytes(result)


def read_source(data, shape):
    unity = UnityFile(data)
    obj = unity.named('SpeechManager')
    return unity, obj, SpeechTable(unity.raw(obj), shape)


def rebuild(data, shape, texts, language=True, additions=()):
    unity, obj, table = read_source(data, shape)
    replacements = {obj['id']: table.rewrite(texts, language, additions)}
    if language:
        # Two serialized MenuCycle option arrays, independently profiled by object ID.
        for pid in shape['language_menu_objects']:
            target = next((x for x in unity.objects if x['id'] == pid), None)
            require(target is not None and target['type'][0] == 114, 'Missing language menu')
            raw = unity.raw(target)
            marker = struct.pack('<I', 2) + pack_string('English') + pack_string('Français')
            require(raw.count(marker) == 1, 'Language menu options changed')
            replacements[pid] = raw.replace(marker, struct.pack('<I', 2) +
                pack_string('Português (Brasil)') + pack_string('Français'))
    output = unity.rewrite(replacements)
    # Reparse translated records with a derived suffix, not a guessed string scan.
    output_unity = UnityFile(output)
    native = output_unity.raw(output_unity.named('SpeechManager'))
    derived = dict(shape)
    if language:
        derived['speech_suffix_b64'] = base64.b64encode(replacement_suffix(shape)).decode()
        derived['translation_count'] = 2
    check = SpeechTable(native, derived)
    require(len(check.rows) == len(table.rows) + len(additions), 'Rebuild count mismatch')
    for old, new in zip(table.rows, check.rows):
        if language:
            require(new['FR'] == old['FR'] and new['PTBR_runtime'] == texts[old['line_id']],
                    'PTBR mismatch or original French translation changed')
        else:
            require(new['FR'] == texts.get(old['line_id'], old['FR']), 'Text mismatch after rebuild')
        for key in ('line_id', 'player', 'scene', 'owner', 'EN', 'description', 'kind'):
            require(old[key] == new[key], 'Immutable native field changed: ' + key)
    for supplied, new in zip(additions, check.rows[len(table.rows):]):
        require(new['line_id'] == supplied['line_id'] and new['EN'] == supplied['EN']
                and new['PTBR_runtime'] == supplied['PTBR'] and new['FR'] == supplied.get('FR', supplied['EN'])
                and new['kind'] == 'Speech' and new['owner'] == supplied['owner']
                and new['scene'] == supplied['scene'] and new['player'] == supplied['player']
                and new['description'] == supplied['description'],
                'Appended translation registration differs')
    return output


def catalog(data, shape):
    _, _, table = read_source(data, shape)
    by_id = {r['line_id']: r for r in table.rows}
    records = []
    for row in table.rows:
        context = {'scene': row['scene'], 'owner': row['owner'], 'is_player': row['player'],
                   'description': row['description'], 'text_type': row['kind'],
                   'speaker': row['owner'] if row['kind'] == 'Speech' else None,
                   'speaker_evidence': 'SpeechLine.owner; verify non-dialogue credits/narration',
                   'speaker_gender': 'unknown', 'addressee': 'unknown',
                   'referent_gender': 'unknown',
                   'context_limits': 'Owner is not gender evidence; no runtime gender selector verified'}
        evidence = shape.get('context_evidence', {}).get(row['owner'])
        if evidence and row['kind'] == 'Speech':
            reference = by_id.get(evidence['line_id'])
            if reference and reference['EN'] == evidence['EN']:
                context['speaker_gender'] = evidence['gender']
                context['gender_evidence'] = evidence
        context['identifier_clues'] = {'owner': row['owner'], 'scene': row['scene'],
                                      'description': row['description']}
        if row['line_id'] in (229, 1346):
            context['referent_evidence'] = {'source_id': row['line_id'], 'text': row['EN'],
                'note': 'Pronouns refer to described characters, not automatically to speaker'}
        records.append({'id': f'{DEPLOY}#SpeechLine:{row["line_id"]}',
                        'key': row['line_id'], 'row': row['order'], 'source_file': DEPLOY,
                        'EN': row['EN'], 'FR': row['FR'], 'context': context, 'PTBR': ''})
    return records
