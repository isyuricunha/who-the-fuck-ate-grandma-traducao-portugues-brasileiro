"""Strict adapter for the actual TMP subtitle atlas (sharedassets0 PathID 458).

Font427 is the source face, not the atlas used by TextMeshProUGUI. Retain the
original static glyphs and append native-engine-baked Portuguese glyphs.
"""
import struct
from native import require

GLYPH = struct.Struct('<I5f4ifii')
CHARACTER = struct.Struct('<IIIf')
RECT = struct.Struct('<4i')


def parse(raw):
    # Exact stripped profile: TMP 1.1.0, original SCUMM face at 68 points.
    require(raw[60:65] == b'1.1.0', 'Unknown TMP subtitle profile')
    require(struct.unpack_from('<f', raw, 112)[0] == 68, 'Unexpected TMP point size')
    pos = 392
    def array(fmt):
        nonlocal pos
        count = struct.unpack_from('<I', raw, pos)[0]; pos += 4
        require(count < 10000 and pos + count * fmt.size <= len(raw), 'Invalid TMP array')
        values = [fmt.unpack_from(raw, pos + i * fmt.size) for i in range(count)]
        pos += count * fmt.size
        return values
    glyphs = array(GLYPH); characters = array(CHARACTER); tables_end = pos
    require(struct.unpack_from('<Iiq', raw, pos) == (1, 0, 201), 'Unexpected TMP atlas reference')
    pos += 48
    used = array(RECT); free = array(RECT)
    return dict(glyphs=glyphs, characters=characters, used=used, free=free,
                tables_end=tables_end, rects_end=pos)


def compile_asset(original, bake):
    old = parse(original)
    require(len(old['glyphs']) == len(old['characters']) == 86, 'Unknown original TMP inventory')
    require(bake['ok'] and not bake['missing'], 'Incomplete native TMP bake')
    glyphs = [(g['index'], *g['metrics'], *g['rect'], g['scale'], g['atlas'], g['class'])
              for g in bake['glyphs']]
    characters = [(c['type'], c['unicode'], c['glyph'], c['scale']) for c in bake['characters']]
    require(len({g[0] for g in glyphs}) == len(glyphs), 'Duplicate TMP glyph')
    require(len({c[1] for c in characters}) == len(characters), 'Duplicate TMP character')
    new_glyphs = {g[0]: g for g in glyphs}; new_chars = {c[1]: c for c in characters}
    for g in old['glyphs']: require(new_glyphs.get(g[0]) == g, 'Original TMP glyph changed')
    for c in old['characters']: require(new_chars.get(c[1]) == c, 'Original TMP character changed')
    require(all(c[2] in new_glyphs for c in characters), 'Dangling TMP glyph reference')
    require(all(g[11] == 0 for g in glyphs), 'Unexpected additional atlas')
    for g in glyphs:
        x, y, w, h = g[6:10]
        require(0 <= x < 2048 and 0 <= y < 1024 and x+w <= 2048 and y+h <= 1024,
                'TMP glyph outside atlas')
    prefix = bytearray(original[:392])
    # Preserve point size, x-height and cap height. Make room for full-height
    # accents/cedilla in multi-line text, instead of compressing the glyphs.
    struct.pack_into('<ff', prefix, 124, 102, 85)
    struct.pack_into('<f', prefix, 144, -17)
    tail = bytearray(original[old['tables_end']:old['tables_end']+48])
    require(struct.unpack_from('<4i', tail, 32) == (1024, 1024, 27, 4134), 'Unknown TMP atlas settings')
    struct.pack_into('<i', tail, 32, 2048)
    def array(fmt, values):
        return struct.pack('<I', len(values)) + b''.join(fmt.pack(*v) for v in values)
    # Static in the shipped asset. No runtime code or instrumentation is needed.
    return (bytes(prefix) + array(GLYPH, glyphs) + array(CHARACTER, characters) + bytes(tail)
            + array(RECT, bake['used']) + array(RECT, bake['free']) + original[old['rects_end']:])
