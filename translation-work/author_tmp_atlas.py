"""Optional Windows developer bake using a private copy of this game's engine.

No instrumentation is shipped. Normal builds consume reviewed static snapshots.
Requires the optional requirements-engine-bake.txt, plus a verified PTBR build.
"""
import argparse
import json
from pathlib import Path
import shutil
import threading
import frida
from native import UnityFile, sha, require
from toolkit import Project

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / 'translation-work/visuals'
DATA = 'Who the fuck ate grandma_Data/'


def main(game, output):
    p = Project(ROOT); p.integrity(); receipt = p.verify_output()
    require(game.resolve() != ROOT.resolve(), 'Expected a read-only game installation')
    output = output.resolve()
    require(output.is_relative_to(ROOT / 'translation-work/.state'), 'Bake output must stay in .state')
    output.mkdir(parents=True, exist_ok=True)
    sandbox = output / 'game'
    if not sandbox.exists(): shutil.copytree(game, sandbox)
    # Always start from the reviewed build, then restore the original three TMP
    # objects. This also works when rebaking after the corrected atlas exists.
    for rel in receipt['output']:
        dest = sandbox / rel; dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / 'PTBR' / rel, dest)
    source = UnityFile((WORK / 'original/sharedassets0.assets').read_bytes())
    current_path = sandbox / DATA / 'sharedassets0.assets'
    current = UnityFile(current_path.read_bytes())
    objects = {o['id']: o for o in source.objects}
    original_ids = {201, 458, 2}
    restored = current.rewrite({i: source.raw(objects[i]) for i in original_ids})
    current_path.write_bytes(restored)
    old = (WORK / 'tmp/original-alpha8.bin').read_bytes()
    require(sha(old) == 'c65241b22be529709d3918c2b084de6a62be936a87f8e937011432ce3558c881',
            'Unknown original atlas pixels')
    (output / 'original-alpha8.bin').write_bytes(old)
    _, records, _, _ = p.workspace()
    needed = ''.join(sorted({c for r in records.values() for c in r['PTBR'] if ord(c) > 32}))
    (output / 'needed.txt').write_text(needed, 'utf-8')
    code = (ROOT / 'translation-work/bake_tmp_engine.js').read_text('utf-8')
    code = code.replace('__INPUT__', output.as_posix())
    event = threading.Event(); result = {}; errors = []
    def receive(message, data):
        value = message.get('payload', {})
        if value.get('stage') == 'result':
            result.update(value)
            if data: (output / 'atlas-alpha8.bin').write_bytes(data)
            event.set()
        elif message.get('type') == 'error' or value.get('stage') in ('error', 'setup-error'):
            errors.append(message); event.set()
    device = frida.get_local_device()
    exe = sandbox / 'Who the fuck ate grandma.exe'
    pid = device.spawn([str(exe), '-batchmode', '-nographics', '-logFile', str(output / 'engine.log')],
                       cwd=str(sandbox))
    try:
        session = device.attach(pid); script = session.create_script(code)
        script.on('message', receive); script.load(); device.resume(pid)
        require(event.wait(40), 'Native font bake timed out')
        require(not errors, 'Native font bake failed: ' + str(errors))
        require(result.get('ok') and not result.get('missing'), 'Incomplete native font bake')
        (output / 'bake.json').write_bytes((json.dumps(result, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
    finally:
        try: device.kill(pid)
        except frida.ProcessNotFoundError: pass
    print(json.dumps({'output': str(output), 'glyphs': len(result['glyphs']),
                      'characters': len(result['characters']), 'installation_written': False}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'translation-work/.state/tmp-bake')
    args = parser.parse_args(); main(args.game_root, args.output)
