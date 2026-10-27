"""Dirty-file transactions with bounded, verified local rollback receipts."""
import contextlib
import json
import os
from pathlib import Path
import shutil
import socket
import time
import uuid

from native import require, sha


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode()


def canonical(data):
    return data.replace(b'\r\n', b'\n')


def safe(root, relative):
    p = Path(relative)
    require(not p.is_absolute() and '..' not in p.parts and ':' not in relative
            and '\\' not in relative, 'Unsafe relative path: ' + relative)
    target = root / p
    for part in [root, *target.parents, target]:
        require(not part.is_symlink() and not getattr(part, 'is_junction', lambda: False)(),
                'Symlink/junction prohibited: ' + str(part))
    require(target.resolve().is_relative_to(root.resolve()), 'Path escapes repository')
    return target


def durable(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp-' + uuid.uuid4().hex)
    try:
        with temp.open('xb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        if os.name != 'nt':
            fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
    finally:
        temp.unlink(missing_ok=True)


def digest(path):
    return sha(path.read_bytes()) if path.is_file() else None


def alive(pid):
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.windll.kernel32
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x1000 | 0x00100000, False, pid)
        if not handle:
            return False
        try:
            return kernel.WaitForSingleObject(handle, 0) == 258
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


class Store:
    def __init__(self, root, count=10, budget=512 * 1024 * 1024):
        self.root = Path(root).resolve()
        self.base = safe(self.root, 'translation-work/.state')
        self.count, self.budget = count, budget
        require(isinstance(count, int) and count >= 1 and isinstance(budget, int) and budget > 0,
                'Retention count/byte limits must be positive and bounded')

    @contextlib.contextmanager
    def lock(self, recover=False):
        self.base.mkdir(parents=True, exist_ok=True)
        p = self.base / 'lock.json'
        if p.exists() and recover:
            old = json.loads(p.read_text('utf-8'))
            require(old['host'] == socket.gethostname() and not alive(old['pid']),
                    'Lock owner still active or belongs to another host; do not break it')
            p.unlink()
        try:
            with p.open('x', encoding='utf-8') as f:
                json.dump({'pid': os.getpid(), 'host': socket.gethostname()}, f)
        except FileExistsError:
            raise ValueError('Another operation holds lock; use recover after confirmed interruption')
        try:
            yield
        finally:
            p.unlink(missing_ok=True)

    def receipts(self):
        result = []
        for folder in sorted(self.base.glob('txn-*')):
            require(not folder.is_symlink() and not getattr(folder, 'is_junction', lambda: False)(),
                    'Unsafe transaction folder')
            p = folder / 'journal.json'
            require(p.is_file(), 'Incomplete transaction preparation; preserve ' + str(folder))
            j = json.loads(p.read_text('utf-8'))
            require(j.get('schema') == 1 and j.get('id') == folder.name,
                    'Corrupt transaction ownership receipt')
            total = 0
            expected = {'journal.json'}
            for i, entry in enumerate(j['files']):
                safe(self.root, entry['path'])
                expected.add(f'{i}.before') if entry['before'] is not None else None
                backup = folder / f'{i}.before'
                require((j['status'] == 'preparing' and not backup.exists())
                        or digest(backup) == entry['before'], 'Corrupt rollback backup')
                if backup.exists():
                    total += backup.stat().st_size
                expected.add(f'{i}.after')
            require(all(x.name in expected and x.is_file() and not x.is_symlink()
                        for x in folder.iterdir()), 'Unexpected transaction contents; cleanup blocked')
            total += p.stat().st_size
            result.append((folder, j, total))
        return result

    def assert_ready(self):
        require(all(j['status'] in ('complete', 'rolled_back') for _, j, _ in self.receipts()),
                'Pending transaction: run recover before changing work')

    def stats(self):
        receipts = self.receipts()
        total, remaining, reclaimable = sum(n for _, _, n in receipts), len(receipts), 0
        if all(j['status'] in ('complete', 'rolled_back') for _, j, _ in receipts):
            for _, _, size in receipts[:-1]:
                if remaining <= self.count and total <= self.budget:
                    break
                reclaimable += size; total -= size; remaining -= 1
        return {'transactions': len(receipts), 'completed': sum(j['status'] == 'complete'
                for _, j, _ in receipts), 'protected': sum(j['status'] not in
                ('complete', 'rolled_back') for _, j, _ in receipts),
                'bytes': sum(n for _, _, n in receipts),
                'max_count': self.count, 'max_bytes': self.budget, 'reclaimable_bytes': reclaimable}

    def gc(self, dry=False):
        self.assert_ready()
        receipts = self.receipts()
        total, remaining, remove = sum(n for _, _, n in receipts), len(receipts), []
        # Always keep the latest receipt, including its sole pre-operation state.
        for folder, j, size in receipts[:-1]:
            if remaining <= self.count and total <= self.budget:
                break
            remove.append({'id': j['id'], 'status': j['status'], 'bytes': size})
            total -= size
            remaining -= 1
            if not dry:
                require(folder.resolve().parent == self.base.resolve(), 'Cleanup escape')
                shutil.rmtree(folder)
        require(total <= self.budget and remaining <= self.count,
                'Retention budget cannot preserve latest recovery state; increase configured limits')
        return {'dry_run': dry, 'eligible': remove, 'reclaimable_bytes': sum(x['bytes'] for x in remove)}

    def commit(self, updates, expected=None, fault=None):
        self.assert_ready()
        changes, before_data = {}, {}
        for rel, data in updates.items():
            path = safe(self.root, rel)
            old = path.read_bytes() if path.exists() else None
            if expected is not None and rel in expected:
                require((sha(old) if old is not None else None) == expected[rel],
                        'Concurrent edit detected: ' + rel)
            if data != old:
                changes[rel], before_data[rel] = data, old
        if not changes:
            return None
        needed = sum(len(d or b'') + len(before_data[p] or b'') for p, d in changes.items())
        require(sum(len(d or b'') for d in before_data.values()) + 65536 <= self.budget,
                'Transaction exceeds retention budget; configure a larger bounded budget')
        require(shutil.disk_usage(self.root).free > needed * 2 + 16 * 1024 * 1024,
                'Insufficient free space for staging and recovery')
        self.gc()
        folder = self.base / ('txn-' + str(time.time_ns()) + '-' + uuid.uuid4().hex[:8])
        folder.mkdir(parents=True)
        j = {'schema': 1, 'id': folder.name, 'status': 'preparing', 'files': [
            {'path': rel, 'before': sha(before_data[rel]) if before_data[rel] is not None else None,
             'after': sha(data) if data is not None else None} for rel, data in changes.items()]}
        # A preparation receipt is created first; a crash never produces a prunable orphan.
        durable(folder / 'journal.json', encoded(j))
        for i, (rel, data) in enumerate(changes.items()):
            old = before_data[rel]
            if old is not None:
                durable(folder / f'{i}.before', old)
            if data is not None:
                durable(folder / f'{i}.after', data)
        j['status'] = 'pending'
        durable(folder / 'journal.json', encoded(j))
        for i, entry in enumerate(j['files']):
            target = safe(self.root, entry['path'])
            require(digest(target) == entry['before'], 'Concurrent edit during transaction')
            if entry['after'] is None:
                target.unlink(missing_ok=True)
            else:
                durable(target, (folder / f'{i}.after').read_bytes())
            if fault:
                fault(i)
        require(all(digest(safe(self.root, e['path'])) == e['after'] for e in j['files']),
                'Transaction verification failed')
        j['status'] = 'complete'
        durable(folder / 'journal.json', encoded(j))
        for p in folder.glob('*.after'):
            p.unlink()
        self.gc()
        return folder.name

    def restore(self, folder, j):
        for e in j['files']:
            require(digest(safe(self.root, e['path'])) in (e['before'], e['after']),
                    'Conflicting live edit: recovery refuses to overwrite ' + e['path'])
        j['status'] = 'recovering'
        durable(folder / 'journal.json', encoded(j))
        for i, e in enumerate(j['files']):
            target = safe(self.root, e['path'])
            if e['before'] is None:
                target.unlink(missing_ok=True)
            else:
                durable(target, (folder / f'{i}.before').read_bytes())
        j['status'] = 'rolled_back'
        durable(folder / 'journal.json', encoded(j))
        for p in folder.glob('*.after'):
            p.unlink()

    def recover(self, transaction=None):
        recovered = []
        for folder, j, _ in self.receipts():
            if transaction == j['id'] or (transaction is None and j['status'] not in
                                                       ('complete', 'rolled_back')):
                if j['status'] == 'preparing':
                    require(all(digest(safe(self.root, e['path'])) == e['before'] for e in j['files']),
                            'Concurrent edit after interrupted preparation; preserve staging for review')
                    # No promotion may start before pending is durable. Missing backups
                    # can be reconstructed from unchanged live inputs without guessing.
                    for i, e in enumerate(j['files']):
                        if e['before'] is not None and not (folder / f'{i}.before').exists():
                            durable(folder / f'{i}.before', safe(self.root, e['path']).read_bytes())
                self.restore(folder, j)
                recovered.append(j['id'])
        require(transaction is None or transaction in recovered, 'Unknown rollback ID')
        return recovered
