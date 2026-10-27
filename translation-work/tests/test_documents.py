import json
from pathlib import Path
import re
import unittest

from test_toolkit import ROOT, Sandbox
from consent import ATTESTATION
from native import DEPLOY, catalog, rebuild
from toolkit import WORK, load


def public_copy_errors(text):
    # Construct negative-fixture names without publishing persona bylines in docs.
    names = [''.join(map(chr, xs)) for xs in ([69,108,108,97], [83,97,121,117,114,105],
                                             [67,111,100,101,120], [67,104,97,116,71,80,84])]
    errors = []
    if any(re.search(r'\b' + name + r'\b', text, re.I) for name in names):
        errors.append('persona attribution')
    if re.search(r'(?:traduziu|testad[ao]|concluíd[ao])(?:\s+\w+){0,4}\s+(?:por\s+)?Yuri\b', text, re.I):
        errors.append('third-person maintainer narration')
    return errors


class DocumentsTests(unittest.TestCase):
    def test_public_readme_art_badges_license_and_evergreen_download(self):
        text = (ROOT / 'README.md').read_text('utf-8')
        self.assertFalse(public_copy_errors(text))
        self.assertIn('steam/apps/1756100/header.jpg', text)
        self.assertIn('width="650"', text)
        badges = re.findall(r'<a href="([^"]+)"><img alt="([^"]+)" src="(https://img.shields.io/[^"]+)"', text)
        self.assertTrue(2 <= len(badges) <= 5)
        self.assertIn('https://discord.gg/uFEwSMwUYb', text)
        self.assertIn('https://traducao.yuricunha.com/', text)
        self.assertIn('/releases)', text); self.assertNotIn('/releases/latest', text)
        self.assertIn('quando disponível', text)
        for link in ('./LICENSE', './GAME-DEVELOPER-PERMISSION.md', './CONTRIBUTING.md'):
            self.assertIn(link, text)
        for forbidden in ('JSONL', 'batch-000', 'toolkit.py', 'fingerprint', 'TODO', 'INSERIR_LINK', '100%'):
            self.assertNotIn(forbidden, text)
        self.assertLess(text.index('## 📦 Download'), text.index('## 💚 Apoio'))
        self.assertIn('resources.assets', text)

    def test_negative_copy_fixtures_and_neutral_credit(self):
        persona = ''.join(map(chr, [69,108,108,97]))
        self.assertTrue(public_copy_errors('Tradução por ' + persona))
        self.assertTrue(public_copy_errors('Tradução concluída e testada por Yuri'))
        self.assertFalse(public_copy_errors('Coordenação e manutenção: Yuri Cunha.'))

    def test_day_one_licensing_and_unchecked_consent(self):
        legal = (ROOT / 'LICENSE').read_text('utf-8')
        self.assertGreater(len(legal), 20000)
        for n in range(1, 9):
            self.assertIn(f'Section {n}', legal)
        self.assertIn('Attribution-NonCommercial-ShareAlike 4.0 International', legal)
        permission = (ROOT / 'GAME-DEVELOPER-PERMISSION.md').read_text('utf-8')
        for term in ('royalty-free', 'commercial', 'non-exclusive', 'contributor', 'third-party'):
            self.assertIn(term, permission.lower())
        self.assertIn('Who The Fuck Ate Grandma', permission)
        self.assertNotIn('Permissão', permission)
        template = (ROOT / '.github/PULL_REQUEST_TEMPLATE.md').read_text('utf-8')
        self.assertIn(ATTESTATION.replace('[x]', '[ ]'), template)
        self.assertNotIn(ATTESTATION, template)

    def test_workflow_output_only_trigger_and_no_native_rebuild(self):
        workflow = (ROOT / '.github/workflows/release.yml').read_text('utf-8')
        self.assertIn("- 'PTBR/**'", workflow)
        self.assertIn("- 'translation-work/release.py'", workflow)
        self.assertIn("- 'translation-work/project.json'", workflow)
        self.assertIn("- 'translation-work/toolchain.json'", workflow)
        self.assertIn('verify-output', workflow)
        self.assertIn('release.py', workflow)
        self.assertNotIn('toolkit.py build', workflow)
        self.assertNotIn('EN/**', workflow)
        self.assertIn('cancel-in-progress: false', workflow)

    def test_authored_docs_have_no_persona_bylines(self):
        for p in [ROOT / 'README.md', *list((ROOT / 'translation-work').rglob('*.md'))]:
            self.assertFalse(public_copy_errors(p.read_text('utf-8')), str(p))


class RealSourceTests(unittest.TestCase):
    @unittest.skipUnless((ROOT / 'EN' / DEPLOY).exists(), 'Real source snapshot not supplied')
    def test_actual_native_roundtrip_inventory_and_pending(self):
        shape = load(ROOT / WORK / 'engine-shapes.json')
        data = (ROOT / 'EN' / DEPLOY).read_bytes()
        rows = catalog(data, shape)
        manifest = load(ROOT / 'translation-work/translations/manifest.json')
        expected = manifest['record_count']
        central = expected - manifest.get('unindexed_speech_count', 0)
        self.assertEqual(len(rows), central)
        self.assertEqual(len(set(r['id'] for r in rows)), central)
        self.assertEqual(rebuild(data, shape, {r['key']: r['FR'] for r in rows}, False), data)
        from toolkit import Project
        p = Project(ROOT)
        self.assertEqual(p.status()['total'], expected)
        from sources import source_catalog, build_sources, blobs
        data, records = p.candidate()
        self.assertEqual(len(records), expected)
        reference = [{**r, 'PTBR': r['FR']} for r in records]
        self.assertEqual(build_sources(data, shape, reference, register=False), blobs(data))


if __name__ == '__main__':
    unittest.main()
