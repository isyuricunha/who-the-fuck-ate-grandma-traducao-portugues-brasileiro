"""Validated, idempotent PTBR.zip publishing. No native rebuild in CI."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

from native import DEPLOY, require, sha
from storage import encoded, safe
from toolkit import Project, ROOT, TRANS, WORK, load

PORTAL = 'https://traducao.yuricunha.com/'
DISCORD = 'https://discord.gg/uFEwSMwUYb'


class Git:
    def __init__(self, root):
        self.root = root

    def run(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], stderr=subprocess.PIPE).decode('utf-8').strip()

    def ancestor(self, tag, head):
        # Missing/non-ancestor tags stop release; never silently start a new history.
        commit = self.run('rev-parse', tag + '^{commit}')
        require(subprocess.run(['git', '-C', str(self.root), 'merge-base', '--is-ancestor',
                commit, head], capture_output=True).returncode == 0, 'Non-ancestor release tag: ' + tag)
        return commit

    def records(self, tag):
        manifest = json.loads(self.run('show', f'{tag}:{TRANS}manifest.json'))
        records = {}
        for name in manifest['batches']:
            for line in self.run('show', f'{tag}:{TRANS}{name}').splitlines():
                r = json.loads(line); records[r['id']] = r
        receipt = json.loads(self.run('show', f'{tag}:{WORK}build-manifest.json'))
        return records, receipt


class API:
    def __init__(self, repo, token, base='https://api.github.com'):
        require(re.fullmatch(r'[\w.-]+/[\w.-]+', repo), 'Invalid GitHub repository')
        self.base, self.repo, self.token = base.rstrip('/'), repo, token
        self.root = self.base + '/repos/' + repo

    def request(self, method, endpoint='', data=None, upload=False, missing_ok=False):
        url = endpoint if endpoint.startswith(('http://', 'https://')) else self.root + endpoint
        parsed = urllib.parse.urlparse(url)
        trusted = {urllib.parse.urlparse(self.base).netloc, 'uploads.github.com'}
        require(parsed.netloc in trusted, 'Untrusted upload/API host')
        payload = data if upload else (encoded(data) if data is not None else None)
        headers = {'Accept': 'application/vnd.github+json', 'Authorization': 'Bearer ' + self.token,
                   'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'ptbr-localization-release',
                   'Content-Type': 'application/zip' if upload else 'application/json'}
        for attempt in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, payload, headers, method=method), timeout=45) as response:
                    body = response.read()
                    return json.loads(body) if body else None
            except urllib.error.HTTPError as error:
                code = error.code
                error.close()
                if code == 404 and missing_ok and method == 'GET':
                    return None
                if code >= 500 and method == 'GET' and attempt < 2:
                    time.sleep(attempt + 1); continue
                # Never blindly retry POST: an interrupted draft is recovered next run.
                raise ValueError(f'GitHub {method} {parsed.path}: HTTP {code}; inspect/retry safely') from error
        raise ValueError('GitHub request exhausted retries')

    def releases(self):
        result, page = [], 1
        while True:
            chunk = self.request('GET', f'/releases?per_page=100&page={page}')
            result += chunk
            if len(chunk) < 100:
                return result
            page += 1


def changes(current, receipt, previous=None, previous_receipt=None):
    if previous is None:
        return '## Nesta versão\n\nPrimeiro pacote completo de textos em PT-BR para a base indicada.\n'
    groups = {}
    for key in sorted(set(current) | set(previous)):
        a, b = previous.get(key), current.get(key)
        if a == b:
            continue
        if a and b and a['PTBR'] == b['PTBR'] and a['EN'] == b['EN'] and a['context'] == b['context']:
            continue
        kind = (b or a).get('context', {}).get('text_type', '')
        category = {'Speech': 'Diálogos', 'DialogueOption': 'Opções de diálogo',
                    'MenuElement': 'Interface', 'CursorIcon': 'Interface',
                    'InventoryItem': 'Itens', 'Hotspot': 'Interações',
                    'Character': 'Nomes de personagens', 'JournalEntry': 'Diário'}.get(kind, 'Textos revisados')
        groups[category] = groups.get(category, 0) + 1
    result = '## Mudanças\n\n'
    for category, number in sorted(groups.items()):
        result += f'- **{category}:** {number} entradas adicionadas, removidas ou revisadas.\n'
    if receipt['output'] != previous_receipt['output']:
        result += '- **Recursos do jogo:** arquivo de tradução atualizado; conteúdo nativo revalidado.\n'
    require(groups or receipt['output'] != previous_receipt['output'], 'No meaningful output/text changes')
    return result


def notes(repo, tag, receipt, change_text, previous_tag=None):
    url = 'https://github.com/' + repo
    body = change_text + '\n## Download e instalação\n\n'
    body += f'Baixe **[PTBR.zip]({url}/releases/download/{tag}/PTBR.zip)**. '
    body += 'Feche o jogo, faça backup de `resources.assets`, `level2` e `level4` até `level13` em `Who the fuck ate grandma_Data` '
    body += 'e extraia o ZIP na pasta do executável, aceitando a substituição. '
    body += 'Selecione **Português (Brasil)** nas opções de idioma. '
    body += f'Consulte o [guia de instalação]({url}#instalacao).\n\n'
    body += 'O pacote substitui a opção de inglês pelo PT-BR e preserva o francês. '
    body += 'A validação do pacote não equivale a um teste de jogabilidade ou de fontes.\n\n'
    if previous_tag:
        body += f'[Comparar versões]({url}/compare/{previous_tag}...{tag})\n\n'
    body += f'## Ajuda\n\n[Comunidade Vai Brasil]({DISCORD}) · [Portal de traduções]({PORTAL})\n'
    return body


def make_zip(project, path):
    receipt = project.verify_output()
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for rel in sorted(receipt['output']):
            raw = safe(project.root, 'PTBR/' + rel).read_bytes()
            info = zipfile.ZipInfo(rel, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
    with zipfile.ZipFile(path) as archive:
        require(archive.namelist() == sorted(receipt['output']) and archive.testzip() is None,
                'Invalid ZIP inventory or CRC')
    return path.read_bytes()


def publish(project, api, git):
    project.integrity()
    receipt = project.verify_output()
    rights = project.config['redistribution']
    require(rights['authorized'] is True,
            'Redistribution blocked: the maintainer has not authorized publishing game resources')
    require(not git.run('status', '--porcelain'), 'Release requires a clean committed checkout')
    head = git.run('rev-parse', 'HEAD')
    repo = project.config['repository']
    require(api.repo == repo, 'Repository mismatch')
    metadata = api.request('GET')  # canonical repository root: no trailing slash
    branch = metadata['default_branch']

    def fresh():
        current = api.request('GET', '/branches/' + urllib.parse.quote(branch, safe=''))
        require(current['commit']['sha'] == head, 'Stale runner: default branch advanced')
    fresh()
    releases = api.releases()
    versions = []
    for release in releases:
        match = re.fullmatch(r'v(\d+)\.(\d+)\.(\d+)', release['tag_name'])
        if match:
            versions.append((tuple(map(int, match.groups())), release))
    versions.sort(key=lambda x: x[0])
    key = sha(encoded({'output': receipt['output'], 'texts': receipt['translation_fingerprint']}))
    marker = '<!-- ptbr-build:' + key + ' -->'
    published = [(v, r) for v, r in versions if not r['draft']]
    for _, r in published:
        git.ancestor(r['tag_name'], head)
    previous = published[-1][1] if published else None
    if previous and marker in previous.get('body', ''):
        assets = api.request('GET', f'/releases/{previous["id"]}/assets')
        require(len(assets) == 1 and assets[0]['name'] == 'PTBR.zip', 'Unexpected published Release asset')
        return {'status': 'unchanged', 'tag': previous['tag_name']}
    old_records, old_receipt = git.records(previous['tag_name']) if previous else (None, None)
    _, current, _, _ = project.workspace()
    text = changes(current, receipt, old_records, old_receipt)
    tag = 'v1.0.0' if not published else 'v%d.%d.%d' % (published[-1][0][0], published[-1][0][1], published[-1][0][2] + 1)
    drafts = [r for _, r in versions if r['draft']]
    require(len(drafts) <= 1, 'Multiple interrupted drafts require review')
    tag_ref = api.request('GET', '/git/ref/tags/' + urllib.parse.quote(tag, safe=''), missing_ok=True)
    if tag_ref:
        require(bool(drafts) and tag_ref['object']['type'] == 'commit'
                and tag_ref['object']['sha'] == head,
                'Existing/conflicting tag: inspect orphan or non-ancestor tag before publication')
    if drafts:
        release = drafts[0]
        require(release['tag_name'] == tag and release['target_commitish'] == head
                and marker in release.get('body', ''), 'Conflicting draft; inspect before retry')
    else:
        body = notes(repo, tag, receipt, text, previous['tag_name'] if previous else None) + '\n' + marker
        release = api.request('POST', '/releases', {'tag_name': tag, 'target_commitish': head,
            'name': 'Tradução PT-BR — ' + tag, 'body': body, 'draft': True, 'prerelease': False})
    fresh()
    raw = make_zip(project, project.root / WORK / '.release/PTBR.zip')
    assets = api.request('GET', f'/releases/{release["id"]}/assets')
    require(len(assets) <= 1 and all(a['name'] == 'PTBR.zip' for a in assets), 'Unexpected Release asset; allowlist is PTBR.zip only')
    if assets:
        asset = assets[0]
        # API digest avoids downloading assets and redirecting credentials.
        require(asset.get('digest') == 'sha256:' + sha(raw) and asset['size'] == len(raw),
                'Interrupted draft asset differs or has no verified digest; inspect it before retry')
    else:
        upload = release['upload_url'].split('{')[0] + '?name=PTBR.zip'
        api.request('POST', upload, raw, upload=True)
    assets = api.request('GET', f'/releases/{release["id"]}/assets')
    require(len(assets) == 1 and assets[0]['name'] == 'PTBR.zip' and assets[0]['size'] == len(raw)
            and assets[0].get('digest') == 'sha256:' + sha(raw), 'Uploaded asset not confirmed')
    fresh()
    api.request('PATCH', f'/releases/{release["id"]}', {'draft': False, 'make_latest': 'true'})
    return {'status': 'published', 'tag': tag, 'asset': 'PTBR.zip'}


if __name__ == '__main__':
    try:
        project = Project(ROOT)
        require(os.environ.get('GITHUB_REPOSITORY') == project.config['repository'], 'Must run in configured repository')
        token = os.environ.get('GITHUB_TOKEN', '')
        require(bool(token), 'Missing GITHUB_TOKEN')
        print(json.dumps(publish(project, API(project.config['repository'], token), Git(ROOT)), ensure_ascii=True))
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=True), file=sys.stderr)
        raise SystemExit(1)
