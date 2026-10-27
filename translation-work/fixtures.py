"""Valid synthetic native resource; contains no copied game dialogue/media."""
import base64
import struct
from native import pack_string


def fixture(shape, entries=None):
    if entries is None:
        entries = [dict(id=10, en='Fixture {0}', fr='Reference {0}', owner='Speaker_Jessica',
                        scene='ScriptJessica', desc='Synthetic verified first-person fixture')]
    speech = base64.b64decode(shape['speech_prefix_b64']) + struct.pack('<i', len(entries))
    for r in entries:
        speech += struct.pack('<ii', 0, r['id'])
        for s in (r.get('scene', 'FixtureScene'), r.get('owner', 'Unknown'), r['en'], r['desc'] if 'desc' in r else ''):
            speech += pack_string(s)
        speech += struct.pack('<ii', r.get('kind', 0), 1) + pack_string(r.get('fr', r['en'])) + bytes(52)
    speech += base64.b64decode(shape['speech_suffix_b64'])
    menu = bytes(28) + pack_string('FixtureMenu') + struct.pack('<i', 2) + pack_string('English') + pack_string('Français')
    objects = [(1705, speech)] + [(pid, menu) for pid in shape['language_menu_objects']]
    return container(objects)


def scene_fixture(line_id=-1, message='Unindexed fixture speech', delta=112):
    prefix = bytearray(bytes(28) + pack_string('ActionSpeech') + bytes(delta))
    start = len(prefix)
    struct.pack_into('<iiiiiiq', prefix, start - 32, 0, -1, -1, 1, -1, 0, 0)
    raw = prefix + pack_string(message) + struct.pack('<i', line_id) + bytes(64)
    return container([(9001, bytes(raw))])


def container(objects):
    meta = b'6000.2.9f1\0' + struct.pack('<iBi', 19, 0, 1)
    meta += struct.pack('<iBh', 114, 0, 6) + bytes(32) + struct.pack('<i', len(objects))
    payload = bytearray()
    for pid, raw in objects:
        meta += bytes(-(48 + len(meta)) % 4)
        payload += bytes(-len(payload) % 16)
        meta += struct.pack('<qQIi', pid, len(payload), len(raw), 0)
        payload += raw
    # script refs, externals, ref-types and user-info, retained opaque by adapter.
    meta += bytes(13)
    start = (48 + len(meta) + 15) // 16 * 16
    header = bytearray(48)
    struct.pack_into('>I', header, 8, 22)
    struct.pack_into('>IQQ', header, 20, len(meta), start + len(payload), start)
    return bytes(header) + meta + bytes(start - 48 - len(meta)) + payload
