"""Optional developer tests: inspect and rasterize the actual compiled OTF."""
import io
from pathlib import Path
import struct
import sys
import unicodedata
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from native import UnityFile
try:
    from fontTools.ttLib import TTFont
    from fontTools.pens.recordingPen import RecordingPen
    from fontTools.pens.boundsPen import BoundsPen
    from PIL import Image,ImageDraw,ImageFont,ImageChops
    AVAILABLE=True
except ImportError:
    AVAILABLE=False

ROOT=Path(__file__).resolve().parents[2]


@unittest.skipUnless(AVAILABLE,'Optional fonttools/Pillow authoring dependencies absent')
class FontGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path=ROOT/'translation-work/visuals/fonts/font-427-ptbr.otf'
        cls.font=TTFont(cls.path);cls.cmap=cls.font.getBestCmap()
        u=UnityFile((ROOT/'EN/Who the fuck ate grandma_Data/resources.assets').read_bytes())
        raw=u.raw(next(o for o in u.objects if o['id']==427));start=raw.index(b'OTTO')
        size=struct.unpack_from('<I',raw,start-4)[0]
        cls.original=TTFont(io.BytesIO(raw[start:start+size]))

    def test_accented_bodies_match_base_letter_pixels_at_multiple_sizes(self):
        for size in (12,16,20,24,32):
            face=ImageFont.truetype(str(self.path),size)
            for accented in 'áàâãíóôõúçÁÀÂÃÉÊÍÓÔÕÚÇ':
                base=unicodedata.normalize('NFD',accented)[0]
                height=1750 if base.isupper() else 1250
                def body(ch):
                    im=Image.new('L',(100,100));ImageDraw.Draw(im).text((20,70),ch,font=face,fill=255,anchor='ls')
                    return im.crop((0,70-round(height*size/2000),100,70))
                with self.subTest(size=size,letter=accented):
                    self.assertIsNone(ImageChops.difference(body(base),body(accented)).getbbox())
                    self.assertEqual(face.getlength(base),face.getlength(accented))

    def test_i_stem_is_the_original_continuous_contour(self):
        def first_path(name):
            p=RecordingPen();self.font.getGlyphSet()[name].draw(p)
            end=next(i for i,(op,args) in enumerate(p.value) if op=='closePath')
            return p.value[:end+1]
        self.assertEqual(first_path(self.cmap[ord('i')]),first_path(self.cmap[ord('í')]))
        self.assertEqual(self.cmap[ord('í')],'iacute')

    def test_original_glyphs_and_advances_are_unchanged(self):
        for cp,name in self.original.getBestCmap().items():
            a=RecordingPen();b=RecordingPen()
            self.original.getGlyphSet()[name].draw(a)
            self.font.getGlyphSet()[self.cmap[cp]].draw(b)
            self.assertEqual(a.value,b.value,chr(cp))
            self.assertEqual(self.original['hmtx'][name],self.font['hmtx'][self.cmap[cp]])

    def test_vertical_metrics_contain_all_glyphs_without_shrinking(self):
        gs=self.font.getGlyphSet()
        for name in self.font.getGlyphOrder():
            p=BoundsPen(gs);gs[name].draw(p)
            if p.bounds:
                self.assertGreaterEqual(self.font['hhea'].ascent,p.bounds[3])
                self.assertLessEqual(self.font['hhea'].descent,p.bounds[1])
                self.assertGreaterEqual(self.font['head'].yMax,p.bounds[3])
                self.assertLessEqual(self.font['head'].yMin,p.bounds[1])
        self.assertEqual(self.font['OS/2'].sCapHeight,1750)
        self.assertEqual(self.font['OS/2'].sxHeight,1250)
