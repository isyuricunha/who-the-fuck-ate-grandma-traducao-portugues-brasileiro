import base64
import copy
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from native import DEPLOY, SpeechTable, UnityFile, catalog, read_source, rebuild, sha
from fixtures import fixture
from storage import Store, canonical, digest, encoded, safe
from toolkit import CATALOG, MANIFEST, TRANS, WORK, ROOT, Project, lines, load, validate_text
from consent import ATTESTATION, validate


def seal(root):
    names = ['native.py', 'sources.py', 'storage.py', 'toolkit.py', 'fixtures.py', 'release.py',
             'consent.py', 'visuals.py', 'engine-shapes.json', 'project.json']
    files = {WORK + n: sha(canonical((root / WORK / n).read_bytes())) for n in names}
    toolchain = encoded({'schema': 1, 'files': files})
    (root / WORK / 'toolchain.json').write_bytes(toolchain)
    (root / WORK / 'runtime-support.json').write_bytes(encoded({'schema': 1,
        'python': '>=3.10', 'dependencies': [], 'target': 'Ubuntu 24.04 ARM64',
        'live_arm64': 'pending', 'toolchain': {'path': WORK + 'toolchain.json', 'sha256': sha(toolchain)}}))


class Sandbox(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        w = self.root / WORK; w.mkdir()
        for name in ['native.py', 'sources.py', 'storage.py', 'toolkit.py', 'fixtures.py', 'release.py',
                     'consent.py', 'visuals.py', 'engine-shapes.json', 'project.json']:
            shutil.copyfile(ROOT / WORK / name, w / name)
        self.shape = load(w / 'engine-shapes.json')
        self.shape.pop('scene_resources', None)
        (w / 'engine-shapes.json').write_bytes(encoded(self.shape))
        self.p = Project(self.root)
        seal(self.root)

    def init(self, entries=None, cap=500):
        self.p.config['batch_size'] = cap
        data = fixture(self.shape, entries)
        result = self.p.synchronize(data, catalog(data, self.shape), initial=True)
        return result

    def payload(self, values):
        m, rows, _, _ = self.p.workspace()
        return {'generation': m['generation'], 'entries': [{'id': k, 'PTBR': v} for k, v in values.items()]}

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def complete(self):
        _, records, _, _ = self.p.workspace()
        # Synthetic fixtures only. Never write artificial translation to real batches.
        return self.p.apply(self.payload({k: r['EN'] + ' áãõç' for k, r in records.items()}))


class NativeTests(Sandbox):
    def test_fixture_noop_and_resize_utf8(self):
        data = fixture(self.shape)
        u, obj, table = read_source(data, self.shape)
        self.assertEqual(rebuild(data, self.shape, {10: 'Reference {0}'}, False), data)
        out = rebuild(data, self.shape, {10: 'Teste comprido áãõç {0} ' * 10})
        self.assertNotEqual(out, data)
        out_u = UnityFile(out)
        self.assertEqual(len(out_u.objects), len(u.objects))
        self.assertIn('Português (Brasil)'.encode(), out_u.raw(out_u.named('SpeechManager')))
        for other in u.objects:
            if other['id'] in self.shape['language_menu_objects']:
                self.assertIn('Português (Brasil)'.encode(), out_u.raw(next(x for x in out_u.objects if x['id'] == other['id'])))

    def test_reject_corrupt_container_and_duplicate_ids(self):
        data = bytearray(fixture(self.shape))
        struct.pack_into('>Q', data, 24, len(data) + 1)
        with self.assertRaisesRegex(ValueError, 'bounds'):
            UnityFile(bytes(data))
        dupe = fixture(self.shape, [{'id': 1, 'en': 'One'}, {'id': 1, 'en': 'Two'}])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            catalog(dupe, self.shape)

    def test_unknown_schema_rejected(self):
        data = fixture(self.shape)
        u = UnityFile(data); obj = u.named('SpeechManager'); raw = bytearray(u.raw(obj)); raw[80] ^= 1
        with self.assertRaisesRegex(ValueError, 'header differs'):
            catalog(u.rewrite({obj['id']: raw}), self.shape)

    def test_ids_not_english_deduplication(self):
        self.init([{'id': 1, 'en': 'Same'}, {'id': 2, 'en': 'Same'}])
        self.assertEqual(self.p.status()['total'], 2)

    def test_gender_clues_roles_and_dynamic_unknown(self):
        entries = [{'id': 229, 'en': 'She has the privilege of having Josiane as her first name.'},
                   {'id': 1, 'en': 'I am tired.', 'owner': 'Josiane'},
                   {'id': 2, 'en': 'He is tired.', 'owner': 'Josiane'},
                   {'id': 3, 'en': 'I am tired.', 'owner': 'Speaker_Jessica', 'scene': 'ScriptJessica'},
                   {'id': 4, 'en': 'I am tired.', 'owner': 'PlayerSelectableGender'},
                   {'id': 5, 'en': 'I am tired.', 'owner': 'AmbiguousName'},
                   {'id': 6, 'en': 'I am tired.', 'owner': 'Speaker_Daniel'}]
        self.init(entries)
        _, rows, _, _ = self.p.workspace()
        vals = list(rows.values())
        self.assertEqual(vals[1]['context']['speaker_gender'], 'female')
        self.assertEqual(vals[2]['context']['referent_gender'], 'unknown')
        self.assertEqual(vals[3]['context']['identifier_clues']['scene'], 'ScriptJessica')
        for n in (3, 4, 5):
            self.assertEqual(vals[n]['context']['speaker_gender'], 'unknown')
        self.assertEqual(vals[6]['context']['identifier_clues']['owner'], 'Speaker_Daniel')

    def test_unmanaged_en_file_is_rejected_without_accepting_generation(self):
        self.init()
        extra = self.root / 'EN/new-localization.assets'; extra.write_bytes(b'unknown profile')
        data = fixture(self.shape)
        old = (self.root / MANIFEST).read_bytes()
        with self.assertRaisesRegex(ValueError, 'Unexpected/missing EN'):
            self.p.synchronize(data, catalog(data, self.shape))
        self.assertEqual(old, (self.root / MANIFEST).read_bytes())

    def test_protected_tokens_and_nested_tags(self):
        validate_text('<b>Hello {0} [wait:1]</b>', '<b>Olá {0} [wait:1]</b>')
        for text in ['Olá', '<b>Hello {0} [wait:1]', '<b><i>{0}</b></i>']:
            with self.assertRaises(ValueError):
                validate_text('<b>Hello {0} [wait:1]</b>', text)
        validate_text('<b><i>{0}</i></b>', '<b><i>{0}</i></b>')

    def test_percentages_in_prose_and_real_printf_tokens(self):
        validate_text('Consider a 3% discount.', 'Considere um desconto de 3%.')
        validate_text('98% certainty.', '98% de certeza.')
        validate_text('100% real!', '100% de verdade!')
        validate_text('3% discount; balance % d.', 'Desconto de 3%; saldo % d.')
        for source, target in [('Balance % d.', 'Saldo d.'),
                               ('Balance % dkg.', 'Saldo %skg.'),
                               ('Code 1%d.', 'Código 1%s.'),
                               ('Total %02d.', 'Total %d.'),
                               ('Value %1$.2f.', 'Valor %1$.2d.')]:
            with self.subTest(source=source), self.assertRaises(ValueError):
                validate_text(source, target)


class WorkflowTests(Sandbox):
    def test_exact_initial_batching_and_preserve_duplicates(self):
        entries = [{'id': n, 'en': 'Synthetic text'} for n in range(1001)]
        self.init(entries)
        m, _, batches, _ = self.p.workspace()
        self.assertEqual([len(b) for b in batches.values()], [500, 500, 1])
        self.assertEqual(m['record_count'], 1001)
        self.assertFalse((self.root / 'PTBR').exists())

    def test_partial_apply_errors_overwrite_and_generation(self):
        self.init([{'id': 1, 'en': 'Hello {0}'}, {'id': 2, 'en': 'World'}])
        _, records, _, _ = self.p.workspace(); keys = list(records)
        result = self.p.apply(self.payload({keys[0]: 'Olá {0}', keys[1]: 'Errado {0}'}))
        self.assertEqual(len(result['applied']), 1); self.assertEqual(len(result['rejected']), 1)
        result = self.p.apply(self.payload({keys[0]: 'Outra {0}'}))
        self.assertTrue(result['rejected'])
        self.assertFalse(self.p.apply(self.payload({keys[0]: 'Outra {0}'}), replace=True)['rejected'])
        payload = self.payload({keys[1]: 'Mundo'}); payload['generation'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'generation'):
            self.p.apply(payload)
        payload = self.payload({keys[1]: 'Mundo'}); payload['entries'] *= 2
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.p.apply(payload)

    def test_source_and_context_tampering_fail(self):
        self.init(); m, rows, batches, _ = self.p.workspace()
        b = self.root / TRANS / next(iter(batches))
        changed = list(rows.values()); changed[0]['context']['owner'] = 'someone-else'; b.write_bytes(lines(changed))
        with self.assertRaisesRegex(ValueError, 'Immutable'):
            self.p.workspace()

    def test_one_source_change_reorder_add_remove_history(self):
        original = [{'id': n, 'en': f'Text {n}'} for n in range(5)]
        self.init(original, cap=2); self.complete()
        _, before, _, old_owners = self.p.workspace()
        modified = [original[3], original[1], {'id': 2, 'en': 'Changed'}, original[0], {'id': 9, 'en': 'New'}]
        data = fixture(self.shape, modified)
        result = self.p.synchronize(data, catalog(data, self.shape))
        _, after, _, owners = self.p.workspace()
        for key in after.keys() & before.keys():
            self.assertEqual(owners[key], old_owners[key])
            self.assertEqual(bool(after[key]['PTBR']), after[key]['key'] != 2)
        self.assertEqual(result['counts']['modified'], 1)
        self.assertEqual(result['counts']['removed'], 1)
        old_changed = next(e for e in result['entries'] if e['classification'] == 'modified')
        self.assertTrue(old_changed['previous']['PTBR'])
        self.assertTrue(list((self.root / WORK / 'history').glob('*.json')))

    def test_gender_context_change_requires_review(self):
        entries = [{'id': 229, 'en': 'She has the privilege of having Josiane as her first name.'},
                   {'id': 1, 'en': 'I am tired.', 'owner': 'Josiane'}, {'id': 2, 'en': 'Other', 'owner': 'Unknown'}]
        self.init(entries); self.complete()
        entries[0]['en'] = 'Different context'
        data = fixture(self.shape, entries); result = self.p.synchronize(data, catalog(data, self.shape))
        self.assertEqual(result['counts']['modified'], 2)
        _, rows, _, _ = self.p.workspace()
        self.assertTrue(next(x for x in rows.values() if x['key'] == 2)['PTBR'])

    def test_manual_en_replacement_and_noop(self):
        self.init([{'id': 1, 'en': 'Before'}]); self.complete()
        data = fixture(self.shape, [{'id': 1, 'en': 'After'}])
        (self.root / 'EN' / DEPLOY).write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'EN differs'):
            self.p.workspace()
        self.p.synchronize(data, catalog(data, self.shape))
        before = self.snapshot()
        self.assertEqual(self.p.synchronize(data, catalog(data, self.shape))['status'], 'unchanged')
        self.assertEqual(before, self.snapshot())

    def test_dry_run_is_read_only(self):
        self.init(); before = self.snapshot()
        data = fixture(self.shape, [{'id': 10, 'en': 'Changed'}])
        self.p.synchronize(data, catalog(data, self.shape), dry=True)
        self.p.store.gc(dry=True)
        self.assertEqual(before, self.snapshot())

    def test_readonly_game_import_and_fallback(self):
        game = self.root / 'separate game path'; (game / DEPLOY).parent.mkdir(parents=True)
        (game / DEPLOY).write_bytes(fixture(self.shape))
        (game / 'Who the fuck ate grandma_Data/app.info').write_text('Wrong\nGame\n')
        with self.assertRaisesRegex(ValueError, 'identity'):
            self.p.candidate(game=game)
        # candidate rejects nested repository paths even if the title matches.
        (game / 'Who the fuck ate grandma_Data/app.info').write_text('Grandma Industries\nWho the fuck ate grandma\n')
        with self.assertRaisesRegex(ValueError, 'external'):
            self.p.candidate(game=game)
        self.p.config['game_candidates'] = []
        with self.assertRaisesRegex(ValueError, '--game-root'):
            self.p.discover()

    def test_incomplete_build_complete_fixture_build_and_staleness(self):
        self.init()
        with self.assertRaisesRegex(ValueError, 'pending'):
            self.p.build()
        self.assertFalse((self.root / 'PTBR').exists())
        self.complete(); self.p.build(); self.p.verify_output()
        before = (self.root / 'PTBR' / DEPLOY).read_bytes()
        _, records, _, _ = self.p.workspace(); key = next(iter(records))
        self.p.apply(self.payload({key: 'Changed {0}'}), replace=True)
        self.assertEqual((self.root / 'PTBR' / DEPLOY).read_bytes(), before)
        with self.assertRaisesRegex(ValueError, 'Stale'):
            self.p.verify_output()
        self.p.build(); self.p.verify_output()
        (self.root / 'PTBR' / DEPLOY).write_bytes(b'tamper')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            self.p.verify_output()

    def test_concurrent_edit_during_planning(self):
        self.init(); expected = self.p.expectations()
        b = next((self.root / TRANS).glob('batch-*.jsonl')); b.write_bytes(b.read_bytes() + b'\n')
        with self.assertRaisesRegex(ValueError, 'Concurrent'):
            self.p.current_guard(expected)

    def test_500_tiny_updates_101_batches_storage_bounds(self):
        self.init([{'id': n, 'en': f'Text {n}'} for n in range(101)], cap=1)
        _, records, _, owners = self.p.workspace()
        target = next(iter(records)); other = self.root / TRANS / sorted(set(owners.values()))[-1]
        stamp = other.stat().st_mtime_ns; raw = other.read_bytes()
        for n in range(500):
            self.p.apply(self.payload({target: f'Synthetic {n}'}), replace=True)
        stats = self.p.store.stats()
        self.assertLessEqual(stats['transactions'], 10)
        self.assertLess(stats['bytes'], 100000)
        self.assertEqual(stamp, other.stat().st_mtime_ns)
        self.assertEqual(raw, other.read_bytes())
        self.assertEqual(self.p.status()['completed'], 1)


class RecoveryTests(Sandbox):
    def test_crash_during_preparation_recovers_without_losing_inputs(self):
        from unittest.mock import patch
        import storage
        (self.root / 'a').write_bytes(b'old-a'); (self.root / 'b').write_bytes(b'old-b')
        real = storage.durable
        def stop(path, data):
            if path.name == '0.after':
                raise RuntimeError('crash during staging')
            return real(path, data)
        with patch('storage.durable', side_effect=stop):
            with self.assertRaises(RuntimeError):
                self.p.store.commit({'a': b'new-a', 'b': b'new-b'})
        self.assertTrue(self.p.store.recover())
        self.assertEqual((self.root / 'a').read_bytes(), b'old-a')
        self.assertEqual((self.root / 'b').read_bytes(), b'old-b')
        self.p.store.gc()

    def test_symlink_escape_is_rejected(self):
        link = self.root / 'escape'
        try:
            link.symlink_to(self.root.parent, target_is_directory=True)
        except OSError:
            self.skipTest('OS does not permit creating symlinks for this account')
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            safe(self.root, 'escape/file')

    def test_budget_refuses_single_oversize_recovery_state(self):
        (self.root / 'a').write_bytes(b'x' * 100000)
        store = Store(self.root, budget=70000)
        with self.assertRaisesRegex(ValueError, 'retention budget'):
            store.commit({'a': b'new'})
        self.assertEqual((self.root / 'a').stat().st_size, 100000)

    def test_crash_rolls_back_only_dirty_files(self):
        store = self.p.store
        a = self.root / 'a'; a.write_bytes(b'before')
        def crash(i):
            if i == 0:
                raise RuntimeError('simulated power loss')
        with self.assertRaises(RuntimeError):
            store.commit({'a': b'after', 'b': b'new'}, fault=crash)
        with self.assertRaisesRegex(ValueError, 'Pending'):
            store.gc(dry=True)
        self.assertTrue(store.recover())
        self.assertEqual(a.read_bytes(), b'before'); self.assertFalse((self.root / 'b').exists())

    def test_recovery_refuses_unrelated_live_edit(self):
        def crash(_):
            raise RuntimeError()
        with self.assertRaises(RuntimeError):
            self.p.store.commit({'a': b'after'}, fault=crash)
        (self.root / 'a').write_bytes(b'user edit')
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            self.p.store.recover()

    def test_receipt_corruption_prevents_gc(self):
        (self.root / 'a').write_bytes(b'old')
        self.p.store.commit({'a': b'new'})
        backup = next(self.p.store.base.glob('txn-*/*.before')); backup.write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'Corrupt'):
            self.p.store.gc()

    def test_path_escape_and_low_disk(self):
        for path in ('../bad', 'C:/bad', '/bad', 'a\\b'):
            with self.assertRaises(ValueError):
                safe(self.root, path)
        from unittest.mock import patch
        with patch('storage.shutil.disk_usage') as disk:
            disk.return_value.free = 0
            with self.assertRaisesRegex(ValueError, 'Insufficient'):
                self.p.store.commit({'a': b'new'})
        self.assertFalse((self.root / 'a').exists())

    def test_explicit_rollback_and_noop(self):
        (self.root / 'a').write_bytes(b'old')
        tx = self.p.store.commit({'a': b'new'})
        self.assertIsNone(self.p.store.commit({'a': b'new'}))
        self.p.store.recover(tx)
        self.assertEqual((self.root / 'a').read_bytes(), b'old')


class IntegrityTests(Sandbox):
    def test_nested_lf_hashes_crlf_and_tampering(self):
        self.init()
        for name in ['engine-shapes.json', 'toolchain.json', 'runtime-support.json']:
            p = self.root / WORK / name; p.write_bytes(p.read_bytes().replace(b'\n', b'\r\n'))
        self.p.integrity()
        p = self.root / WORK / 'engine-shapes.json'; p.write_bytes(p.read_bytes().replace(b'6000.2', b'6000.3'))
        with self.assertRaisesRegex(ValueError, 'checksum'):
            self.p.integrity()

    def test_git_index_normalization_in_fresh_checkout(self):
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        (self.root / '.gitattributes').write_bytes(b'* text=auto eol=lf\nEN/** -text\n')
        p = self.root / WORK / 'engine-shapes.json'; raw = p.read_bytes(); p.write_bytes(raw.replace(b'\n', b'\r\n'))
        original = self.root / 'EN/native'; original.parent.mkdir(); original.write_bytes(b'native\r\nbytes\0')
        subprocess.run(['git', '-C', str(self.root), 'add', '.'], check=True, capture_output=True)
        blob = subprocess.check_output(['git', '-C', str(self.root), 'show', ':translation-work/engine-shapes.json'])
        self.assertEqual(sha(blob), sha(canonical(raw)))
        native_blob = subprocess.check_output(['git', '-C', str(self.root), 'show', ':EN/native'])
        self.assertEqual(native_blob, b'native\r\nbytes\0')
        p.unlink(); subprocess.run(['git', '-C', str(self.root), 'checkout-index', '-f', '--all'], check=True)
        self.p.integrity()

    def test_doctor_valid_fixture_and_readonly(self):
        self.init(); before = self.snapshot()
        result = self.p.doctor('host')
        self.assertEqual(result['status'], 'ok'); self.assertEqual(before, self.snapshot())
        if sys.platform != 'linux':
            with self.assertRaisesRegex(ValueError, 'architecture'):
                self.p.doctor()
        native = self.root / 'EN' / DEPLOY; native.write_bytes(native.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'EN differs'):
            self.p.doctor('host')

    def test_contributor_opt_in(self):
        commits = [{'sha': 'abc', 'author': {'login': 'contributor'}}]
        with self.assertRaises(ValueError):
            validate('', 'contributor', commits)
        self.assertTrue(validate(ATTESTATION, 'contributor', commits))
        with self.assertRaisesRegex(ValueError, 'co-contributor'):
            validate(ATTESTATION, 'someone', commits)
        self.assertTrue(validate(ATTESTATION, 'someone', commits,
            [{'login': 'contributor', 'commits': ['abc'], 'affirmative': True, 'evidence_url': 'https://example.org/consent'}]))


if __name__ == '__main__':
    unittest.main()
