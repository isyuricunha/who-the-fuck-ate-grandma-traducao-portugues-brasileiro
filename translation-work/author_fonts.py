"""Developer-only vector font authoring. Requires fonttools; build does not.

Original ASCII outlines/advances stay intact. New SCUMM characters use its
250-unit pixel grid; accented bodies preserve their original full height.
"""
import io
import json
from pathlib import Path
import struct
import unicodedata

from fontTools.ttLib import TTFont
from fontTools.agl import UV2AGL
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.transformPen import TransformPen
from native import UnityFile, sha

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'translation-work/visuals/fonts'


def recording(font, name):
    p = RecordingPen(); font.getGlyphSet()[name].draw(p)
    return p


def bounds(font, name):
    gs = font.getGlyphSet(); p = BoundsPen(gs); gs[name].draw(p)
    return p.bounds


def rectangle(pen, x, y, w, h):
    pen.moveTo((x, y)); pen.lineTo((x, y+h))
    pen.lineTo((x+w, y+h)); pen.lineTo((x+w, y)); pen.closePath()


def add(font, cp, draw, advance, bearing=0, glyph_name=None):
    name = glyph_name or f'uni{cp:04X}'
    assert name not in font.getGlyphOrder(), ('Glyph name collision', name)
    p = T2CharStringPen(advance, font.getGlyphSet()); draw(p)
    top = font['CFF '].cff.topDictIndex[0]
    char = p.getCharString(private=top.Private, globalSubrs=font['CFF '].cff.GlobalSubrs)
    cs = top.CharStrings
    cs.charStrings[name] = len(cs.charStringsIndex)
    cs.charStringsIndex.append(char)
    top.charset.append(name)
    font.setGlyphOrder(top.charset)
    font['hmtx'].metrics[name] = (advance, bearing)
    font['maxp'].numGlyphs = len(top.charset)
    for table in font['cmap'].tables:
        if table.isUnicode(): table.cmap[cp] = name


def scumm(font, cp):
    c = chr(cp); decomp = unicodedata.normalize('NFD', c)
    base, mark = decomp[0], decomp[1]
    cm = font.getBestCmap(); name = cm[ord(base)]
    advance = font['hmtx'][name][0]
    b = bounds(font, name); center = round((b[0]+b[2])/2/250)*250
    body = recording(font, name)
    if base == 'i':
        # Remove only the independent dot contour. Preserve the continuous
        # stem/serif path exactly; do not rebuild it as separate pixel cells.
        stem = RecordingPen()
        for op, args in body.value:
            getattr(stem, op)(*args)
            if op in ('closePath', 'endPath'): break
        body = stem
    accent_y = 2000 if base.isupper() else 1500
    def draw(p):
        body.replay(p)
        if mark == '\u0327':
            rectangle(p, center, -250, 250, 250)
            rectangle(p, center-250, -500, 500, 250)
        elif mark in ('\u0301', '\u0300'):
            offsets = [(-500, accent_y), (0, accent_y+250)]
            if mark == '\u0300': offsets = [(0, accent_y), (-500, accent_y+250)]
            for x, y in offsets: rectangle(p, center+x, y, 500, 250)
        elif mark == '\u0302':
            rectangle(p, center-500, accent_y, 250, 250)
            rectangle(p, center+250, accent_y, 250, 250)
            rectangle(p, center-250, accent_y+250, 500, 250)
        elif mark == '\u0303':
            for y, row in [(accent_y+250, '11001'), (accent_y, '00110')]:
                for x, filled in enumerate(row):
                    if filled == '1': rectangle(p, center-500+x*250, y, 250, 250)
        else: raise ValueError(('Unsupported accent', c))
    add(font, cp, draw, advance, font['hmtx'][name][1], glyph_name=UV2AGL.get(cp))


def chunk_tilde(font, cp):
    base = chr(cp).replace('õ', 'o').replace('Õ', 'O')
    accent_source = 'ã' if base == 'o' else 'Ã'
    cm = font.getBestCmap(); base_name = cm[ord(base)]; accent_name = cm[ord(accent_source)]
    gs = font.getGlyphSet(); ab = bounds(font, cm[ord(accent_source[0].replace('ã','a').replace('Ã','A'))])
    bb = bounds(font, base_name); whole = recording(font, accent_name)
    chunks = []; current = RecordingPen()
    for op, args in whole.value:
        getattr(current, op)(*args)
        if op in ('closePath', 'endPath'):
            p = BoundsPen(gs); current.replay(p)
            if p.bounds and p.bounds[1] > ab[3]: chunks.append(current)
            current = RecordingPen()
    assert chunks, 'Missing tilde template'
    dx = (bb[0]+bb[2]-ab[0]-ab[2])/2
    def draw(p):
        gs[base_name].draw(p)
        for rec in chunks: rec.replay(TransformPen(p, (1, 0, 0, 1, dx, 0)))
    add(font, cp, draw, *font['hmtx'][base_name])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    raw = (ROOT / 'EN/Who the fuck ate grandma_Data/resources.assets').read_bytes()
    u = UnityFile(raw); report = {}
    texts = ''.join(json.loads(line)['PTBR'] for p in
                    (ROOT / 'translation-work/translations').glob('batch-*.jsonl')
                    for line in p.read_text('utf-8').splitlines())
    for pid in (427, 428):
        obj = next(o for o in u.objects if o['id'] == pid); blob = u.raw(obj)
        start = blob.index(b'OTTO'); size = struct.unpack_from('<I', blob, start-4)[0]
        original = blob[start:start+size]; f = TTFont(io.BytesIO(original), recalcTimestamp=False)
        old_cm = f.getBestCmap().copy(); old = {cp: (recording(f, name).value, f['hmtx'][name]) for cp,name in old_cm.items()}
        if pid == 427:
            for c in 'áàâãíóôõúçÁÀÂÃÉÊÍÓÔÕÚÇ':
                if ord(c) not in f.getBestCmap(): scumm(f, ord(c))
            # Unicode minus uses the font's existing minus-shaped hyphen.
            for table in f['cmap'].tables:
                if table.isUnicode(): table.cmap[0x2212] = old_cm[ord('-')]
            def degree(p):
                for y,row in enumerate(('111', '101', '111')):
                    for x,v in enumerate(row):
                        if v == '1': rectangle(p, 250+x*250, 1250+y*250, 250, 250)
            add(f, 0xB0, degree, 1250, 250, glyph_name='degree')
        else:
            for c in 'õÕ': chunk_tilde(f, ord(c))
            for table in f['cmap'].tables:
                if table.isUnicode(): table.cmap[0xB0] = old_cm[0x2DA]
        if pid == 427:
            # Full-size capitals need real vertical room; never fit the glyph
            # into the old box by shrinking its body.
            all_bounds = [bounds(f, name) for name in f.getGlyphOrder()]
            all_bounds = [b for b in all_bounds if b]
            extent = [min(b[0] for b in all_bounds), min(b[1] for b in all_bounds),
                      max(b[2] for b in all_bounds), max(b[3] for b in all_bounds)]
            f['CFF '].cff.topDictIndex[0].FontBBox = extent
            f['head'].xMin, f['head'].yMin, f['head'].xMax, f['head'].yMax = extent
            f['hhea'].ascent = int(extent[3]); f['hhea'].descent = int(extent[1])
            f['OS/2'].sTypoAscender = int(extent[3]); f['OS/2'].sTypoDescender = int(extent[1])
            f['OS/2'].usWinAscent = int(extent[3]); f['OS/2'].usWinDescent = int(-extent[1])
        path = OUT / f'font-{pid}-ptbr.otf'; f.save(path, reorderTables=False)
        check = TTFont(path); cm = check.getBestCmap()
        for cp,(drawing, metrics) in old.items():
            assert recording(check, cm[cp]).value == drawing, ('Original outline changed', pid, cp)
            assert check['hmtx'][cm[cp]] == metrics, ('Original advance changed', pid, cp)
        missing = sorted(set(c for c in texts if ord(c)>32 and ord(c) not in cm))
        assert not missing, (pid, missing)
        report[str(pid)] = {'original_sha256':sha(original), 'output_sha256':sha(path.read_bytes()),
                            'original_characters':len(old_cm), 'characters':len(cm),
                            'added':''.join(chr(cp) for cp in sorted(set(cm)-set(old_cm))),
                            'original_outlines_and_advances_preserved':True,'missing_from_translation':missing}
        if pid == 427:
            scale = 16 / check['head'].unitsPerEm
            report[str(pid)]['full_height_accented_bodies'] = True
            report[str(pid)]['continuous_i_stem'] = True
            report[str(pid)]['unity_cached_metrics'] = {
                'ascent':check['hhea'].ascent*scale,
                'descent':check['hhea'].descent*scale,
                'line_spacing':(check['hhea'].ascent-check['hhea'].descent+check['hhea'].lineGap)*scale}
    (OUT / 'coverage.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__ == '__main__': main()
