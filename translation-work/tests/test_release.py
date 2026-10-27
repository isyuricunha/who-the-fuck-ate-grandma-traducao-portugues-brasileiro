import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import unittest
import zipfile

from test_toolkit import Sandbox, WORK
from native import DEPLOY, sha
from release import API, changes, make_zip, notes, publish


class FakeGit:
    def __init__(self):
        self.head = 'a' * 40
        self.saved = {}
        self.nonancestor = False

    def run(self, *args):
        if args[0] == 'status':
            return ''
        return self.head

    def ancestor(self, tag, head):
        if self.nonancestor:
            raise ValueError('Non-ancestor release tag')
        return self.head

    def records(self, tag):
        return self.saved[tag]


class MockGitHub:
    def __init__(self, head):
        self.releases, self.assets, self.calls = [], {}, []
        self.head, self.fail, self.once500 = head, None, False
        self.tag_ref = None
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                self.handle_request()

            def do_POST(self):
                self.handle_request()

            def do_PATCH(self):
                self.handle_request()

            def send(self, status, value):
                data = json.dumps(value).encode()
                self.send_response(status); self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data)

            def handle_request(self):
                data = self.rfile.read(int(self.headers.get('Content-Length', 0)))
                owner.calls.append((self.command, self.path, data))
                root = '/repos/isyuricunha/who-the-fuck-ate-grandma-traducao-portugues-brasileiro'
                path = self.path.removeprefix(root)
                if owner.fail:
                    return self.send(owner.fail, {'message': 'controlled API failure'})
                if owner.once500 and self.command == 'GET':
                    owner.once500 = False; return self.send(500, {})
                if self.path.startswith('/upload/'):
                    rid = int(self.path.split('/')[2].split('?')[0])
                    asset = {'id': 1, 'name': 'PTBR.zip', 'size': len(data), 'digest': 'sha256:' + sha(data),
                             'url': owner.url + '/asset/1'}
                    owner.assets[rid].append(asset)
                    return self.send(201, asset)
                if path == '' and self.command == 'GET':
                    return self.send(200, {'default_branch': 'main'})
                if path.startswith('/branches/'):
                    return self.send(200, {'commit': {'sha': owner.head}})
                if path.startswith('/releases?'):
                    return self.send(200, owner.releases)
                if path.startswith('/git/ref/tags/'):
                    return self.send(200, owner.tag_ref) if owner.tag_ref else self.send(404, {})
                if path == '/releases' and self.command == 'POST':
                    release = json.loads(data); rid = len(owner.releases) + 1
                    release.update({'id': rid, 'upload_url': owner.url + f'/upload/{rid}' + '{?name,label}'})
                    owner.releases.append(release); owner.assets[rid] = []
                    return self.send(201, release)
                if path.endswith('/assets'):
                    return self.send(200, owner.assets[int(path.split('/')[2])])
                if path.startswith('/releases/') and self.command == 'PATCH':
                    release = next(r for r in owner.releases if r['id'] == int(path.split('/')[2]))
                    release.update(json.loads(data)); return self.send(200, release)
                return self.send(404, {'path': self.path})
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.url = f'http://127.0.0.1:{self.server.server_address[1]}'
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()


class ReleaseTests(Sandbox):
    def setUp(self):
        super().setUp()
        self.init(); self.complete(); self.p.build()
        self.p.config['redistribution'] = {'authorized': True, 'evidence': 'permission.txt'}
        (self.root / 'permission.txt').write_text('Synthetic permission fixture; not real authorization.')
        self.git = FakeGit()
        self.server = MockGitHub(self.git.head); self.addCleanup(self.server.close)
        self.api = API(self.p.config['repository'], 'synthetic-token', self.server.url)

    def save(self, tag):
        _, records, _, _ = self.p.workspace()
        self.git.saved[tag] = (copy.deepcopy(records), copy.deepcopy(self.p.verify_output()))

    def change(self):
        _, records, _, _ = self.p.workspace(); key = next(iter(records))
        self.p.apply(self.payload({key: 'Revisão {0}'}), replace=True); self.p.build()

    def test_actual_http_first_release_zip_and_idempotence(self):
        result = publish(self.p, self.api, self.git)
        self.assertEqual(result['tag'], 'v1.0.0')
        self.assertFalse(self.server.releases[0]['draft'])
        self.assertEqual([a['name'] for a in self.server.assets[1]], ['PTBR.zip'])
        with zipfile.ZipFile(self.root / WORK / '.release/PTBR.zip') as archive:
            self.assertEqual(archive.namelist(), [DEPLOY])
        paths = [p for _, p, _ in self.server.calls]
        root = '/repos/' + self.p.config['repository']
        self.assertIn(root, paths); self.assertNotIn(root + '/', paths)
        self.assertTrue(any(p.startswith('/upload/1?name=PTBR.zip') for p in paths))
        self.assertIn(root + '/releases/1', paths)
        self.assertIn(root + '/git/ref/tags/v1.0.0', paths)
        self.save('v1.0.0')
        result = publish(self.p, self.api, self.git)
        self.assertEqual(result['status'], 'unchanged'); self.assertEqual(len(self.server.releases), 1)

    def test_patch_version_real_dialogue_changelog(self):
        publish(self.p, self.api, self.git); self.save('v1.0.0'); self.change()
        result = publish(self.p, self.api, self.git)
        self.assertEqual(result['tag'], 'v1.0.1')
        body = self.server.releases[-1]['body']
        self.assertIn('Diálogos', body); self.assertIn('/compare/v1.0.0...v1.0.1', body)
        self.assertIn('https://discord.gg/uFEwSMwUYb', body)
        self.assertNotIn('git log', body)

    def test_rights_gate_and_stale_head_no_publish(self):
        self.p.config['redistribution']['authorized'] = False
        with self.assertRaisesRegex(ValueError, 'Redistribution'):
            publish(self.p, self.api, self.git)
        self.assertFalse(self.server.calls)
        self.p.config['redistribution']['authorized'] = True; self.server.head = 'b' * 40
        with self.assertRaisesRegex(ValueError, 'Stale runner'):
            publish(self.p, self.api, self.git)
        self.assertFalse(self.server.releases)

    def test_draft_resume_and_asset_allowlist(self):
        publish(self.p, self.api, self.git)
        self.server.releases[0]['draft'] = True
        result = publish(self.p, self.api, self.git)
        self.assertEqual(result['tag'], 'v1.0.0'); self.assertEqual(len(self.server.releases), 1)
        self.server.assets[1].append({'name': 'LICENSE', 'size': 1})
        with self.assertRaisesRegex(ValueError, 'Unexpected'):
            publish(self.p, self.api, self.git)

    def test_nonancestor_and_conflicting_draft(self):
        publish(self.p, self.api, self.git); self.save('v1.0.0'); self.change()
        self.git.nonancestor = True
        with self.assertRaisesRegex(ValueError, 'Non-ancestor'):
            publish(self.p, self.api, self.git)
        self.git.nonancestor = False
        release = copy.deepcopy(self.server.releases[0]); release.update({'id': 2, 'draft': True, 'tag_name': 'v1.0.1'})
        self.server.releases.append(release)
        with self.assertRaisesRegex(ValueError, 'Conflicting draft'):
            publish(self.p, self.api, self.git)

    def test_http_auth_404_and_get_retry(self):
        for code in (403, 404):
            self.server.fail = code
            with self.assertRaisesRegex(ValueError, str(code)):
                publish(self.p, self.api, self.git)
        self.server.fail = None; self.server.once500 = True
        self.assertEqual(publish(self.p, self.api, self.git)['status'], 'published')

    def test_orphan_tag_and_concurrent_branch_movement_fail_closed(self):
        self.server.tag_ref = {'object': {'type': 'commit', 'sha': 'b' * 40}}
        with self.assertRaisesRegex(ValueError, 'conflicting tag'):
            publish(self.p, self.api, self.git)
        self.assertFalse(self.server.releases)
        self.server.tag_ref = None
        real = self.api.request
        def move_after_create(method, endpoint='', *args, **kwargs):
            result = real(method, endpoint, *args, **kwargs)
            if method == 'POST' and endpoint == '/releases':
                self.server.head = 'b' * 40
            return result
        self.api.request = move_after_create
        with self.assertRaisesRegex(ValueError, 'Stale runner'):
            publish(self.p, self.api, self.git)
        self.assertTrue(self.server.releases[0]['draft'])

    def test_changelog_native_only_and_unknown_category(self):
        _, current, _, _ = self.p.workspace(); receipt = self.p.verify_output()
        old_receipt = copy.deepcopy(receipt); old_receipt['output'][DEPLOY] = 'different'
        self.assertIn('Recursos do jogo', changes(current, receipt, current, old_receipt))
        prior = copy.deepcopy(current); key = next(iter(prior))
        prior[key]['PTBR'] = 'Old {0}'; current[key]['context']['text_type'] = 'Unclassified'
        self.assertIn('Textos revisados', changes(current, receipt, prior, old_receipt))


if __name__ == '__main__':
    unittest.main()
