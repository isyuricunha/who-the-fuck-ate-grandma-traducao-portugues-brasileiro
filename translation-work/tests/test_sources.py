import copy
from pathlib import Path
import shutil
import struct
import unittest

from test_toolkit import Sandbox, ROOT, seal
from fixtures import fixture, scene_fixture
from native import DEPLOY, SpeechTable, UnityFile, read_source
from sources import actions, build_sources, source_catalog
from storage import encoded
from toolkit import Project, WORK


class SceneSourcesTests(Sandbox):
    def sources(self, delta=112):
        self.shape['scene_resources'] = ['Who the fuck ate grandma_Data/level2']
        (self.root / WORK / 'engine-shapes.json').write_bytes(encoded(self.shape))
        self.p = Project(self.root)
        seal(self.root)
        return {DEPLOY: fixture(self.shape), self.shape['scene_resources'][0]: scene_fixture(delta=delta)}

    def test_register_native_ids_preserves_original_messages_and_metadata(self):
        for delta in (112, 156):
            data = self.sources(delta)
            rows = source_catalog(data, self.shape)
            self.assertEqual(len(rows), 2)
            self.assertIn('PathID:9001', rows[-1]['id'])
            reference = [{**r, 'PTBR': r['FR']} for r in rows]
            self.assertEqual(build_sources(data, self.shape, reference, register=False), data)
            translated = [{**r, 'PTBR': r['EN'] + ' áãõç'} for r in rows]
            out = build_sources(data, self.shape, translated)
            scene = self.shape['scene_resources'][0]
            _, old_actions = actions(data[scene]); _, new_actions = actions(out[scene])
            self.assertEqual(old_actions[0]['text'], new_actions[0]['text'])
            self.assertEqual(old_actions[0]['line_id'], -1)
            self.assertEqual(new_actions[0]['line_id'], 11)
            u = UnityFile(out[DEPLOY]); raw = u.raw(u.named('SpeechManager'))
            output_shape = copy.deepcopy(self.shape)
            import base64
            from native import replacement_suffix
            output_shape['speech_suffix_b64'] = base64.b64encode(replacement_suffix(output_shape)).decode()
            output_shape['translation_count'] = 2
            table = SpeechTable(raw, output_shape)
            self.assertEqual(table.rows[-1]['line_id'], new_actions[0]['line_id'])
            self.assertEqual(table.rows[-1]['EN'], old_actions[0]['text'])
            self.assertEqual(table.rows[0]['FR'], 'Reference {0}')
            self.assertEqual(table.rows[-1]['FR'], old_actions[0]['text'])

    def test_english_is_replaced_in_enabled_selector_and_french_preserved(self):
        import base64
        from native import Reader, replacement_suffix, pack_string
        suffix = replacement_suffix(self.shape)
        r = Reader(suffix, 16)
        self.assertEqual(r.i(), 3)
        languages = []
        for _ in range(3):
            name, _ = r.string(); r.i(); r.string(); r.string(); r.i(); disabled = r.i()
            languages.append((name, disabled))
        self.assertEqual(languages, [('English', 1), ('Português (Brasil)', 0), ('Français', 0)])
        self.assertEqual([name for name, disabled in languages if not disabled], ['Português (Brasil)', 'Français'])

    def test_multi_resource_workflow_build_gate_sync_and_missing_file(self):
        data = self.sources(); rows = source_catalog(data, self.shape)
        self.p.synchronize(data, rows, initial=True)
        self.assertEqual(self.p.status()['total'], 2)
        self.complete(); self.p.build(); receipt = self.p.verify_output()
        self.assertEqual(set(receipt['output']), set(data))
        before = (self.root / 'PTBR' / DEPLOY).read_bytes()
        scene = self.shape['scene_resources'][0]
        changed = dict(data); changed[scene] = scene_fixture(message='Changed fallback')
        report = self.p.synchronize(changed, source_catalog(changed, self.shape))
        self.assertEqual(report['counts']['modified'], 1)
        self.assertEqual(self.p.status()['pending'], 1)
        self.assertEqual((self.root / 'PTBR' / DEPLOY).read_bytes(), before)
        (self.root / 'EN' / scene).unlink()
        with self.assertRaisesRegex(ValueError, 'Unexpected/missing EN'):
            self.p.workspace()

    def test_empty_unindexed_action_is_not_a_translation_unit(self):
        data = self.sources(); data[self.shape['scene_resources'][0]] = scene_fixture(message='')
        rows = source_catalog(data, self.shape)
        self.assertEqual(len(rows), 1)

    def test_speaker_identity_is_linked_by_native_reference_not_name_guess(self):
        from fixtures import container
        data = self.sources(); scene = self.shape['scene_resources'][0]
        a = UnityFile(scene_fixture(line_id=10, message='Fixture {0}'))
        b = UnityFile(scene_fixture())
        data[scene] = container([(9100, a.raw(a.objects[0])), (9200, b.raw(b.objects[0]))])
        rows = source_catalog(data, self.shape)
        extra = rows[-1]
        self.assertEqual(extra['context']['owner'], 'Speaker_Jessica')
        self.assertEqual(extra['context']['speaker_evidence']['witness_line_id'], 10)
        self.assertEqual(extra['context']['speaker_gender'], 'unknown')

    def test_unknown_action_tail_and_dynamic_message_fail_closed(self):
        data = self.sources(); scene = self.shape['scene_resources'][0]
        u = UnityFile(data[scene]); obj = u.objects[0]; raw = bytearray(u.raw(obj))
        # Message parameter belongs to runtime logic; do not make up a static translation.
        name_end = 44; start = name_end + 112
        struct.pack_into('<i', raw, start - 24, 3)
        data[scene] = u.rewrite({obj['id']: raw})
        with self.assertRaisesRegex(ValueError, 'Dynamic'):
            source_catalog(data, self.shape)
        raw += bytes(4); data[scene] = u.rewrite({obj['id']: raw})
        with self.assertRaisesRegex(ValueError, 'layout'):
            source_catalog(data, self.shape)


if __name__ == '__main__':
    unittest.main()
