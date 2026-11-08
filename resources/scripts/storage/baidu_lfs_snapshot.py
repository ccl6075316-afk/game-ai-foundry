"""Snapshot CURRENT LFS content to immutable Baidu packs; never change Git filters.

Run prepare, transfer, verify, publish in order. Each phase is resumable from its
on-disk receipt. Credentials remain in the official CLI. No raw CLI logs saved.
"""
import argparse
import concurrent.futures
import hashlib
import io
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import tarfile
import time

ROOT = Path(__file__).resolve().parents[3]
REPOS = {'foundry': ROOT, 'fishing-2d': ROOT / 'projects/fishing-2d'}
REVIEW = ROOT / 'docs/storage/baidu-lfs-20261109'
WORK = ROOT / 'work/baidu-lfs-20261109'
CLI = Path(shutil.which('bdpan') or Path.home() / 'AppData/Local/bdpan/bdpan.exe')
SESSION = '1794148677-34ab58'
CHUNK = 32 * 1024 * 1024
PACK = 128 * 1024 * 1024


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    os.replace(temp, path)


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], encoding='utf8')


def safe_path(root, relative):
    p = root / relative
    if p.is_absolute() and not p.resolve().is_relative_to(root.resolve()):
        raise ValueError('Path outside root')
    for ancestor in [p, *p.parents]:
        if ancestor.is_symlink() or ancestor.is_junction():
            raise ValueError('Linked path is not allowed')
        if ancestor == root:
            break
    return p


def api(*args):
    start = time.monotonic()
    command = [str(CLI), *map(str, args), '--json', '--no-check-update',
               '--agentname', 'codex', '--session-id', SESSION]
    r = subprocess.run(command, capture_output=True, encoding='utf8', errors='replace', timeout=900)
    try:
        value = json.loads(r.stdout)
    except ValueError:
        raise RuntimeError(f'{args[0]}: exit {r.returncode}, non-JSON response (not logged)')
    if r.returncode or isinstance(value, dict) and value.get('code', 0) not in (0, None):
        # Store neither raw responses nor token-bearing URLs.
        message = str(value.get('error', 'CLI error')) if isinstance(value, dict) else 'CLI error'
        message = re.sub(r'https?://\S+', '[URL omitted]', message)
        message = re.sub(r'(?i)(token|secret|code)[=:][^\s&]+', r'\1=[redacted]', message)
        raise RuntimeError(f'{args[0]}: exit {r.returncode}: {message[:300]}')
    return value, round(time.monotonic() - start, 3)


def authenticated():
    state, _ = api('whoami')
    if not (state.get('authenticated') and state.get('has_valid_token')):
        raise RuntimeError('Official interactive login required')


def prepare():
    if (REVIEW / 'manifest.json').exists():
        raise RuntimeError('Snapshot exists; inspect/resume it instead of duplicating')
    objects = {}
    repos = {}
    for name, repo in REPOS.items():
        if git(repo, 'status', '--porcelain', '--untracked-files=no').strip():
            raise RuntimeError(f'Tracked changes in {name}: freeze inputs first')
        rows = json.loads(git(repo, 'lfs', 'ls-files', '--json'))['files']
        files = []
        for row in rows:
            p = safe_path(repo, row['name'])
            if not row['downloaded'] or p.stat().st_size != row['size'] or sha(p) != row['oid']:
                raise RuntimeError(f'Unhydrated/changed LFS file: {name}/{row["name"]}')
            oid = row['oid']
            files.append({'path': row['name'], 'oid': oid, 'bytes': row['size']})
            if oid not in objects:
                objects[oid] = {'bytes': row['size'], 'source_repo': name, 'source_path': row['name']}
        repos[name] = {'head': git(repo, 'rev-parse', 'HEAD').strip(), 'files': files}
        print(f'Hashed {name}: {len(files)} paths', flush=True)
    packs = []
    members = []
    payload = 0

    def finish():
        nonlocal members, payload
        if not members:
            return
        index = len(packs)
        path = WORK / 'send' / f'{index:04d}.tar'
        path.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(path, 'w', format=tarfile.USTAR_FORMAT) as tar:
            for member in members:
                obj = objects[member['oid']]
                source = safe_path(REPOS[obj['source_repo']], obj['source_path'])
                with source.open('rb') as stream:
                    stream.seek(member['offset'])
                    data = stream.read(member['bytes'])
                if len(data) != member['bytes']:
                    raise RuntimeError('Source changed while packing')
                member['sha256'] = hashlib.sha256(data).hexdigest()
                info = tarfile.TarInfo(member['name'])
                info.size = len(data)
                info.mode = 0o644
                tar.addfile(info, io.BytesIO(data))
        packs.append({'index': index, 'sha256': sha(path), 'bytes': path.stat().st_size, 'members': members})
        members = []
        payload = 0

    for oid, obj in sorted(objects.items()):
        for offset in range(0, max(1, obj['bytes']), CHUNK):
            length = min(CHUNK, obj['bytes'] - offset)
            if payload + length > PACK:
                finish()
            members.append({'oid': oid, 'offset': offset, 'bytes': length,
                            'name': f'{oid}/{offset:012d}'})
            payload += length
    finish()
    prefix = 'foundry-lfs-20261109-' + secrets.token_hex(4)
    for pack in packs:
        pack['remote'] = f'{prefix}/packs/{pack["sha256"]}.tar'
    manifest = {'schema': 1, 'format': 'sha256-chunked-ustar-v1', 'date': '2026-11-09',
                'remote_prefix': prefix, 'scope': 'Current LFS pointers only, no historical revisions',
                'repositories': repos, 'objects': objects, 'packs': packs,
                'unique_objects': len(objects), 'unique_bytes': sum(o['bytes'] for o in objects.values()),
                'path_count': sum(len(r['files']) for r in repos.values()),
                'production_filters_changed': False}
    # Decode the actual packs before any network transfer. This also catches
    # source edits that occurred between hashing and packing.
    verify_content(manifest, WORK / 'send')
    save(REVIEW / 'manifest.json', manifest)
    print(json.dumps({k: manifest[k] for k in ('path_count', 'unique_objects', 'unique_bytes', 'remote_prefix')}), flush=True)
    print(f'{len(packs)} packs ready', flush=True)


def verify_content(m, folder):
    hashes = {}
    sizes = {}
    for pack in m['packs']:
        path = folder / f'{pack["index"]:04d}.tar'
        if path.stat().st_size != pack['bytes'] or sha(path) != pack['sha256']:
            raise RuntimeError(f'Pack mismatch: {pack["index"]}')
        with tarfile.open(path, 'r:') as tar:
            entries = tar.getmembers()
            if [x.name for x in entries] != [x['name'] for x in pack['members']]:
                raise RuntimeError('Unexpected tar member list')
            for entry, expected in zip(entries, pack['members']):
                if not entry.isfile() or entry.size != expected['bytes']:
                    raise RuntimeError('Unexpected tar member type/size')
                data = tar.extractfile(entry).read()
                if hashlib.sha256(data).hexdigest() != expected['sha256']:
                    raise RuntimeError('Chunk mismatch')
                oid = expected['oid']
                if expected['offset'] != sizes.get(oid, 0):
                    raise RuntimeError('Non-contiguous object chunks')
                hashes.setdefault(oid, hashlib.sha256()).update(data)
                sizes[oid] = sizes.get(oid, 0) + len(data)
    if set(hashes) != set(m['objects']):
        raise RuntimeError('Object coverage mismatch')
    for oid, obj in m['objects'].items():
        if hashes[oid].hexdigest() != oid or sizes[oid] != obj['bytes']:
            raise RuntimeError(f'Reconstructed object mismatch: {oid}')
    return len(hashes)


def transfer(workers):
    authenticated()
    m = load(REVIEW / 'manifest.json')
    setup = REVIEW / 'remote-setup.json'
    if not setup.exists():
        # Unique prefix: mkdir may be safely retried after an interrupted setup.
        api('mkdir', m['remote_prefix'])
        response, _ = api('mkdir', m['remote_prefix'] + '/packs')
        save(setup, {'ready': True, 'remote_prefix': m['remote_prefix'],
                     'return_markdown': response.get('return_markdown') if isinstance(response, dict) else None})
    remote, _ = api('ls', m['remote_prefix'] + '/packs', '--limit', '1000')
    known = {row['server_filename']: row for row in remote}
    (WORK / 'receive').mkdir(parents=True, exist_ok=True)

    def one(pack):
        index = pack['index']
        receipt_path = REVIEW / 'receipts' / f'{index:04d}.json'
        if receipt_path.exists() and load(receipt_path).get('round_trip_verified'):
            return index, 'previously verified'
        sender = WORK / 'send' / f'{index:04d}.tar'
        receiver = WORK / 'receive' / f'{index:04d}.tar'
        if sha(sender) != pack['sha256']:
            raise RuntimeError('Sender changed')
        receipt = {'index': index, 'sha256': pack['sha256'], 'bytes': pack['bytes'],
                   'remote': pack['remote'], 'round_trip_verified': False}
        if receipt_path.exists():
            previous = load(receipt_path)
            receipt['previous_attempts'] = previous.get('previous_attempts', []) + [
                {k: previous[k] for k in ('upload_seconds', 'download_seconds', 'error') if k in previous}]
        try:
            remote_name = pack['sha256'] + '.tar'
            if remote_name in known:
                if known[remote_name]['size'] != pack['bytes']:
                    raise RuntimeError('Existing remote has unexpected size; refusing overwrite')
                receipt['upload_reused'] = True
            else:
                _, receipt['upload_seconds'] = api('upload', sender, pack['remote'])
            if not receiver.exists():
                _, receipt['download_seconds'] = api('download', pack['remote'], receiver)
            if receiver.stat().st_size != pack['bytes'] or sha(receiver) != pack['sha256']:
                raise RuntimeError('Downloaded pack mismatch; retained for diagnosis, not overwritten')
            receipt['round_trip_verified'] = True
            save(receipt_path, receipt)
            return index, 'verified'
        except Exception as e:
            receipt['error'] = str(e)
            save(receipt_path, receipt)
            raise

    errors = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(one, p): p['index'] for p in m['packs']}
        for count, future in enumerate(concurrent.futures.as_completed(futures), 1):
            try:
                index, message = future.result()
                print(f'{count}/{len(futures)} pack {index:04d} {message}', flush=True)
            except Exception as e:
                errors.append({'index': futures[future], 'error': str(e)})
                print(f'Pack {futures[future]:04d} failed; receipt retained', flush=True)
    save(REVIEW / 'transfer.validation.json', {'ok': not errors, 'errors': errors,
         'packs': len(m['packs']), 'manifest_sha256': sha(REVIEW / 'manifest.json')})
    if errors:
        raise RuntimeError(f'{len(errors)} failed packs: inspect receipts before resuming')


def verify():
    m = load(REVIEW / 'manifest.json')
    if not load(REVIEW / 'transfer.validation.json')['ok']:
        raise RuntimeError('Transfer incomplete')
    count = verify_content(m, WORK / 'receive')
    for name, repo in REPOS.items():
        actual = json.loads(git(repo, 'lfs', 'ls-files', '--json'))['files']
        expected = m['repositories'][name]['files']
        if {(r['name'], r['oid'], r['size']) for r in actual} != {(r['path'], r['oid'], r['bytes']) for r in expected}:
            raise RuntimeError('LFS index changed since snapshot')
        for row in expected:
            if sha(safe_path(repo, row['path'])) != row['oid']:
                raise RuntimeError(f'Current source changed: {name}/{row["path"]}')
    result = {'ok': True, 'manifest_sha256': sha(REVIEW / 'manifest.json'),
              'objects_reconstructed_sha256': count, 'paths_covered': m['path_count'],
              'unique_bytes': m['unique_bytes'], 'packs_downloaded_verified': len(m['packs']),
              'all_current_lfs_sources_unchanged': True, 'second_physical_computer_tested': False,
              'git_filters_changed': False}
    save(REVIEW / 'validation.json', result)
    print(json.dumps(result), flush=True)


def publish():
    authenticated()
    result = load(REVIEW / 'validation.json')
    if not result['ok'] or result['manifest_sha256'] != sha(REVIEW / 'manifest.json'):
        raise RuntimeError('Manifest is not verified')
    m = load(REVIEW / 'manifest.json')
    path = REVIEW / 'manifest.json'
    remote = m['remote_prefix'] + '/manifest-' + sha(path) + '.json'
    # Check exact name before upload: no auto-renamed duplicate on resume.
    listing, _ = api('ls', m['remote_prefix'], '--limit', '1000')
    if remote.rsplit('/', 1)[1] not in {r['server_filename'] for r in listing}:
        api('upload', path, remote)
    destination = WORK / 'manifest-roundtrip.json'
    if not destination.exists():
        api('download', remote, destination)
    if sha(destination) != sha(path):
        raise RuntimeError('Manifest download mismatch')
    save(REVIEW / 'publication.json', {'ok': True, 'remote': remote,
         'sha256': sha(path), 'bytes': path.stat().st_size,
         'packs_return_markdown': load(REVIEW / 'remote-setup.json').get('return_markdown')})
    print('Published manifest; downloaded manifest SHA-256 matches', flush=True)


def restore(destination):
    """Recover to a NEW directory, never overwrite working tree files.

    Expected manifest SHA comes from the committed publication receipt. Tar
    contents are streamed under manifest-controlled paths; never extractall.
    """
    if not destination:
        raise RuntimeError('--destination must name a new directory under work/')
    dest = safe_path(ROOT / 'work', destination)
    if dest.exists():
        raise RuntimeError('Restore destination exists; refusing overwrite')
    m = load(REVIEW / 'manifest.json')
    if sha(REVIEW / 'manifest.json') != load(REVIEW / 'publication.json')['sha256']:
        raise RuntimeError('Manifest publication hash mismatch')
    # Preflight EVERY destination before creating a file.
    paths = {}
    for name, repo in m['repositories'].items():
        if name not in REPOS:
            raise RuntimeError('Unknown repository')
        for row in repo['files']:
            target = safe_path(dest / name, row['path'])
            paths.setdefault(row['oid'], []).append(target)
    if set(paths) != set(m['objects']):
        raise RuntimeError('Path/object coverage mismatch')
    authenticated()
    (WORK / 'receive').mkdir(parents=True, exist_ok=True)
    for pack in m['packs']:
        path = WORK / 'receive' / f'{pack["index"]:04d}.tar'
        if not path.exists():
            api('download', pack['remote'], path)
        if path.stat().st_size != pack['bytes'] or sha(path) != pack['sha256']:
            raise RuntimeError('Restore pack mismatch; retained for inspection')
    verify_content(m, WORK / 'receive')
    dest.mkdir(parents=True, exist_ok=False)
    for pack in m['packs']:
        with tarfile.open(WORK / 'receive' / f'{pack["index"]:04d}.tar', 'r:') as tar:
            for member in pack['members']:
                target = paths[member['oid']][0]
                target.parent.mkdir(parents=True, exist_ok=True)
                mode = 'xb' if member['offset'] == 0 else 'ab'
                if member['offset'] and target.stat().st_size != member['offset']:
                    raise RuntimeError('Restore offset mismatch')
                data = tar.extractfile(member['name']).read()
                if hashlib.sha256(data).hexdigest() != member['sha256']:
                    raise RuntimeError('Restore chunk mismatch')
                with target.open(mode) as out:
                    out.write(data)
    for oid, targets in paths.items():
        if sha(targets[0]) != oid:
            raise RuntimeError('Restored object mismatch')
        for target in targets[1:]:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as out, targets[0].open('rb') as source:
                shutil.copyfileobj(source, out)
            if sha(target) != oid:
                raise RuntimeError('Restored duplicate mismatch')
    save(dest / 'restore.validation.json', {'ok': True, 'paths': m['path_count'],
         'objects': len(paths), 'manifest_sha256': sha(REVIEW / 'manifest.json')})
    print(f'Restored and verified {m["path_count"]} paths in {dest}', flush=True)


def install(destination, apply=False):
    """Preflight all restored assets, then replace matching LFS pointers only."""
    if not destination:
        raise RuntimeError('--destination must name the completed restore directory')
    restored = safe_path(ROOT / 'work', destination)
    m = load(REVIEW / 'manifest.json')
    manifest_hash = sha(REVIEW / 'manifest.json')
    proof = load(restored / 'restore.validation.json')
    if not proof.get('ok') or proof.get('manifest_sha256') != manifest_hash:
        raise RuntimeError('Restore proof does not match the current manifest')
    if load(REVIEW / 'publication.json')['sha256'] != manifest_hash:
        raise RuntimeError('Publication hash mismatch')
    changes = []
    unchanged = 0
    for name, entry in m['repositories'].items():
        repo = REPOS[name]
        if git(repo, 'status', '--porcelain', '--untracked-files=no').strip():
            raise RuntimeError(f'{name}: resolve tracked local changes before installing assets')
        actual = json.loads(git(repo, 'lfs', 'ls-files', '--json'))['files']
        if {(r['name'], r['oid'], r['size']) for r in actual} != {
                (r['path'], r['oid'], r['bytes']) for r in entry['files']}:
            raise RuntimeError(f'{name}: checkout LFS pointers differ from this snapshot')
        for row in entry['files']:
            source = safe_path(restored / name, row['path'])
            target = safe_path(repo, row['path'])
            if source.stat().st_size != row['bytes'] or sha(source) != row['oid']:
                raise RuntimeError(f'Corrupt restore source: {name}/{row["path"]}')
            if target.is_file() and target.stat().st_size == row['bytes'] and sha(target) == row['oid']:
                unchanged += 1
                continue
            pointer = (f'version https://git-lfs.github.com/spec/v1\noid sha256:{row["oid"]}\n'
                       f'size {row["bytes"]}\n').encode('ascii')
            if not target.is_file() or target.stat().st_size != len(pointer) or target.read_bytes() != pointer:
                raise RuntimeError(f'Refusing to overwrite nonmatching content: {name}/{row["path"]}')
            changes.append((source, target, pointer, row['oid']))
    # Every repository/path has passed before the first working-tree write.
    count = 0
    if apply:
        staging = WORK / 'install'
        staging.mkdir(parents=True, exist_ok=True)
        for source, target, pointer, oid in changes:
            temporary = staging / (oid + '-' + secrets.token_hex(6) + '.tmp')
            with temporary.open('xb') as out, source.open('rb') as stream:
                shutil.copyfileobj(stream, out)
            if sha(temporary) != oid or target.read_bytes() != pointer:
                raise RuntimeError('Source/target changed during install; staging retained')
            temporary.chmod(target.stat().st_mode & 0o777)
            os.replace(temporary, target)
            count += 1
        for name, entry in m['repositories'].items():
            for row in entry['files']:
                if sha(safe_path(REPOS[name], row['path'])) != row['oid']:
                    raise RuntimeError('Installed file SHA mismatch')
    report = {'ok': True, 'apply': apply, 'manifest_sha256': manifest_hash,
              'already_present': unchanged, 'eligible': len(changes), 'installed': count,
              'git_filters_changed': False, 'github_lfs_network_requests': 0}
    save(restored / ('install.validation.json' if apply else 'install-preflight.json'), report)
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'transfer', 'verify', 'publish', 'restore', 'install'])
    parser.add_argument('--workers', type=int, default=4, choices=range(1, 5))
    parser.add_argument('--destination', help='Restore/install directory relative to work/')
    parser.add_argument('--apply', action='store_true', help='Install only: replace verified matching LFS pointers')
    args = parser.parse_args()
    if args.action == 'transfer':
        transfer(args.workers)
    elif args.action == 'restore':
        restore(args.destination)
    elif args.action == 'install':
        install(args.destination, args.apply)
    else:
        globals()[args.action]()
