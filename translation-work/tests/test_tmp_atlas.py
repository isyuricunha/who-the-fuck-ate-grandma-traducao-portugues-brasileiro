"""Regression: verify the subtitle's real TMP atlas, not only its source OTF."""
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'translation-work'))
from native import UnityFile, FormatError
from tmp_atlas import parse, compile_asset


class SubtitleAtlasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=ROOT/'translation-work/visuals/tmp'
        u=UnityFile((ROOT/'translation-work/visuals/original/sharedassets0.assets').read_bytes())
        cls.original=u.raw(next(o for o in u.objects if o['id']==458))
        cls.bake=json.loads((cls.base/'bake.json').read_text('utf-8'))

    def test_primary_atlas_covers_every_translated_character(self):
        result=parse(compile_asset(self.original,self.bake));have={c[1] for c in result['characters']}
        for path in (ROOT/'translation-work/translations').glob('batch-*.jsonl'):
            for line in path.read_text('utf-8').splitlines():
                self.assertFalse({ord(c) for c in json.loads(line)['PTBR'] if ord(c)>32}-have)

    def test_original_glyph_records_and_pixels_are_unchanged(self):
        old=parse(self.original);new=parse(compile_asset(self.original,self.bake))
        self.assertEqual(old['glyphs'],new['glyphs'][:len(old['glyphs'])])
        self.assertEqual(old['characters'],new['characters'][:len(old['characters'])])
        a=(self.base/'atlas-alpha8.bin').read_bytes();b=(self.base/'original-alpha8.bin').read_bytes()
        self.assertEqual(len(a),2048*1024)
        self.assertTrue(all(a[y*2048:y*2048+1024]==b[y*1024:(y+1)*1024] for y in range(1024)))

    def test_accented_body_matches_base_in_actual_sdf_atlas(self):
        result=parse(compile_asset(self.original,self.bake));glyphs={g[0]:g for g in result['glyphs']}
        chars={c[1]:c[2] for c in result['characters']};pixels=(self.base/'atlas-alpha8.bin').read_bytes()
        for accented,base in [('á','a'),('ã','a'),('í','i'),('ó','o')]:
            a=glyphs[chars[ord(accented)]];b=glyphs[chars[ord(base)]]
            self.assertEqual(a[5],b[5]) # advance
            for row in range(43):
                left=pixels[(a[7]+row)*2048+a[6]:(a[7]+row)*2048+a[6]+b[8]]
                right=pixels[(b[7]+row)*2048+b[6]:(b[7]+row)*2048+b[6]+b[8]]
                self.assertEqual(bytes(v>127 for v in left),bytes(v>127 for v in right),accented)

    def test_incomplete_or_changed_bake_is_rejected(self):
        bad=json.loads(json.dumps(self.bake));bad['missing']='í'
        with self.assertRaises(FormatError):compile_asset(self.original,bad)
        bad=json.loads(json.dumps(self.bake));bad['glyphs'][0]['metrics'][4]+=1
        with self.assertRaises(FormatError):compile_asset(self.original,bad)
