"""Git LFS standalone transfer agent backed by the official bdpan CLI.

Configuration is local to each Git repository. Stdout is protocol JSON only.
New objects live at a SHA-addressed path; the 2026-11-09 snapshot is a
read-only bootstrap source for objects already present before activation.
"""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / 'work/baidu-lfs-agent'
SNAPSHOT = ROOT / 'docs/storage/baidu-lfs-20261109'
CLI = shutil.which('bdpan') or str(Path.home() / 'AppData/Local/bdpan/bdpan.exe')
REMOTE = 'foundry-lfs-objects-v1'
SESSION = '1794148677-34ab58'
_SNAPSHOT_CACHE = None
_VERIFIED_PACKS = set()


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def cli(*args):
    result = subprocess.run([CLI, *map(str, args), '--json', '--no-check-update',
                             '--agentname', 'codex', '--session-id', SESSION],
                            capture_output=True, text=True, encoding='utf8', errors='replace', timeout=900)
    try:
        response = json.loads(result.stdout)
    except ValueError:
        raise RuntimeError(f'{args[0]} failed: CLI returned non-JSON')
    if result.returncode or isinstance(response, dict) and response.get('code', 0) not in (0, None):
        reason = str(response.get('error', 'CLI error')) if isinstance(response, dict) else 'CLI error'
        reason = re.sub(r'https?://\S+', '[URL]', reason)
        reason = re.sub(r'(?i)(token|secret|code)[=:][^\s&]+', r'\1=[redacted]', reason)
        raise RuntimeError(f'{args[0]} failed: {reason[:250]}')
    return response


def object_path(oid):
    return f'{REMOTE}/{oid[:2]}/{oid}'


def check(oid, size):
    if not re.fullmatch(r'[0-9a-f]{64}', oid) or not isinstance(size, int) or size < 0:
        raise ValueError('Invalid LFS OID or size')


def snapshot_index():
    global _SNAPSHOT_CACHE
    if _SNAPSHOT_CACHE is not None:
        return _SNAPSHOT_CACHE
    manifest = SNAPSHOT / 'manifest.json'
    receipt = json.loads((SNAPSHOT / 'publication.json').read_text(encoding='utf8'))
    if digest(manifest) != receipt['sha256']:
        raise RuntimeError('Bootstrap manifest SHA mismatch')
    state = json.loads(manifest.read_text(encoding='utf8'))
    index = {}
    for pack in state['packs']:
        for member in pack['members']:
            index.setdefault(member['oid'], []).append((pack, member))
    _SNAPSHOT_CACHE = (state, index)
    return _SNAPSHOT_CACHE


def from_snapshot(oid, size, target):
    state, index = snapshot_index()
    if oid not in index or state['objects'][oid]['bytes'] != size:
        raise RuntimeError('Object not in current snapshot or size mismatch')
    written = 0
    with target.open('xb') as output:
        for pack, member in index[oid]:
            pack_file = WORK / 'packs' / (pack['sha256'] + '.tar')
            pack_file.parent.mkdir(parents=True, exist_ok=True)
            if not pack_file.exists():
                cli('download', pack['remote'], pack_file)
            if pack['sha256'] not in _VERIFIED_PACKS:
                if pack_file.stat().st_size != pack['bytes'] or digest(pack_file) != pack['sha256']:
                    raise RuntimeError('Snapshot pack hash mismatch')
                _VERIFIED_PACKS.add(pack['sha256'])
            if member['offset'] != written:
                raise RuntimeError('Snapshot chunk order mismatch')
            with tarfile.open(pack_file, 'r:') as archive:
                info = archive.getmember(member['name'])
                if not info.isfile() or info.size != member['bytes']:
                    raise RuntimeError('Snapshot chunk metadata mismatch')
                data = archive.extractfile(info).read()
            if hashlib.sha256(data).hexdigest() != member['sha256']:
                raise RuntimeError('Snapshot chunk SHA mismatch')
            output.write(data)
            written += len(data)
    if written != size or digest(target) != oid:
        raise RuntimeError('Snapshot object SHA mismatch')


def remote_names(folder):
    try:
        listing = cli('ls', folder, '--limit', '1000')
    except RuntimeError as error:
        if missing(error):
            return None
        raise
    if not isinstance(listing, list):
        raise RuntimeError('Unexpected directory listing')
    return {row['server_filename']: row['size'] for row in listing}


def missing(error):
    message = str(error).lower()
    return any(phrase in message for phrase in ('不存在', '找不到指定', 'not exist', 'not found'))


def upload(oid, size, source):
    check(oid, size)
    WORK.mkdir(parents=True, exist_ok=True)
    path = Path(source)
    if path.stat().st_size != size or digest(path) != oid:
        raise RuntimeError('LFS upload source does not match OID/size')
    root = remote_names(REMOTE)
    if root is None:
        cli('mkdir', REMOTE)
    folder = f'{REMOTE}/{oid[:2]}'
    names = remote_names(folder)
    if names is None:
        cli('mkdir', folder)
        names = {}
    if oid in names:
        if names[oid] != size:
            raise RuntimeError('Existing cloud object has wrong size')
        # Do not trust size alone: read it back and verify SHA.
    else:
        cli('upload', path, object_path(oid))
    with tempfile.NamedTemporaryFile(dir=WORK, prefix='upload-check-', delete=False) as temporary:
        probe = Path(temporary.name)
    probe.unlink()
    try:
        cli('download', object_path(oid), probe)
        if probe.stat().st_size != size or digest(probe) != oid:
            raise RuntimeError('Cloud upload read-back SHA mismatch')
    finally:
        probe.unlink(missing_ok=True)


def download(oid, size):
    check(oid, size)
    WORK.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=WORK, prefix='lfs-', delete=False) as temporary:
        target = Path(temporary.name)
    target.unlink()
    try:
        try:
            cli('download', object_path(oid), target)
        except RuntimeError as error:
            if not missing(error):
                raise
            target.unlink(missing_ok=True)
            from_snapshot(oid, size, target)
        if target.stat().st_size != size or digest(target) != oid:
            raise RuntimeError('Cloud download SHA mismatch')
        return target
    except Exception:
        target.unlink(missing_ok=True)
        raise


def emit(value):
    sys.stdout.write(json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n')
    sys.stdout.flush()


def run():
    WORK.mkdir(parents=True, exist_ok=True)
    init = json.loads(sys.stdin.readline())
    if init.get('event') != 'init' or init.get('operation') not in ('upload', 'download'):
        emit({'error': {'code': 2, 'message': 'Invalid initialization'}})
        return 1
    operation = init['operation']
    emit({})
    for line in sys.stdin:
        request = json.loads(line)
        if request.get('event') == 'terminate':
            return 0
        oid = request.get('oid', '')
        try:
            if request.get('event') != operation:
                raise RuntimeError('Unexpected transfer direction')
            size = request['size']
            if operation == 'upload':
                upload(oid, size, request['path'])
                emit({'event': 'complete', 'oid': oid})
            else:
                path = download(oid, size)
                emit({'event': 'complete', 'oid': oid, 'path': str(path)})
        except Exception as error:
            emit({'event': 'complete', 'oid': oid, 'error': {'code': 2, 'message': str(error)[:300]}})
    return 0


if __name__ == '__main__':
    sys.exit(run())
