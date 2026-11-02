"""Collect this source snapshot only; all paths and network origins are explicit."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import time
import urllib.request

REPO = next(parent for parent in Path(__file__).resolve().parents if (parent / 'cli/gamefactory.py').is_file())
ROOT = REPO / 'resources/fish-database'
WORK = REPO / 'work/fish-database-complete-20261102'
SID = 'fishing-master-cdn-cnformal1-20261102'
DEST = ROOT / 'artifacts' / SID
BASE = 'https://158-xxdyw-hwcdn.bjxuejing.cn/158-xxdyw/knight_res_android/cnformal1/'
assert ROOT.resolve().is_relative_to(REPO) and WORK.resolve().is_relative_to(REPO / 'work')
rows = {s[0]: s for s in (line.split('|') for line in (DEST / 'FilesMD5.txt').read_text().splitlines())}
WORK.mkdir(parents=True, exist_ok=True)
catalog = [json.loads(line) for line in (ROOT / 'catalogs/fishing-master-xiaomi-20260814/entries.jsonl').read_text().splitlines()]
dependencies = {parts[0]: parts[1:] for parts in (line.split('|') for line in (DEST / 'BundleDependency.txt').read_text().splitlines())}
closure = {name for entry in catalog for name in entry['bundle_paths']}
queue = list(closure)
while queue:
    for dependency in dependencies.get(queue.pop(), []):
        if dependency not in closure:
            closure.add(dependency)
            queue.append(dependency)
plan = {'closure': sorted(closure)}
progress_path = ROOT / 'progress.json'
progress = {'schema_version': 1, 'command': 'collect-game-reference', 'source_id': SID,
            'status': 'running', 'next_action': 'poll', 'stage': 'download',
            'target_base_name_count': 325, 'planned_resource_count': len(plan['closure']),
            'resources': [], 'failures': []}

def save():
    temp = progress_path.with_suffix('.json.tmp')
    temp.write_text(json.dumps(progress, ensure_ascii=False, indent=2) + '\n')
    temp.replace(progress_path)

def acquire(name):
    row = rows[name]
    target = DEST / Path(name).name
    assert target.resolve().is_relative_to(DEST.resolve())
    expected_size, expected_md5 = int(row[2]), row[1].lower()
    result = {'resource_path': name, 'path': str(target.relative_to(ROOT)),
              'url': BASE + name, 'expected_bytes': expected_size,
              'manifest_md5': expected_md5, 'dlc_tag': row[3]}
    if target.exists():
        b = target.read_bytes()
        if len(b) == expected_size and hashlib.md5(b).hexdigest() == expected_md5:
            return result | {'ok': True, 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest(), 'acquisition': 'verified_existing'}
        return result | {'ok': False, 'error': 'Existing canonical file differs from snapshot; not overwritten'}
    temp = WORK / (Path(name).name + '.part')
    for attempt in range(3):
        try:
            md5, sha, size = hashlib.md5(), hashlib.sha256(), 0
            with urllib.request.urlopen(BASE + name, timeout=40) as response, temp.open('wb') as output:
                headers = {k: response.headers.get(k) for k in ('Last-Modified', 'ETag')}
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > expected_size:
                        raise ValueError('Response larger than manifest')
                    output.write(chunk); md5.update(chunk); sha.update(chunk)
            if size != expected_size or md5.hexdigest() != expected_md5:
                raise ValueError(f'Manifest mismatch: bytes={size}, md5={md5.hexdigest()}')
            temp.replace(target)
            return result | {'ok': True, 'bytes': size, 'sha256': sha.hexdigest(),
                             'headers': headers, 'acquisition': 'downloaded'}
        except Exception as exc:
            error = f'{type(exc).__name__}: {exc}'
            temp.unlink(missing_ok=True)
            if attempt < 2:
                time.sleep(attempt + 1)
    return result | {'ok': False, 'error': error}

save()
start = time.monotonic()
with ThreadPoolExecutor(max_workers=6) as pool:
    futures = [pool.submit(acquire, name) for name in plan['closure']]
    for future in as_completed(futures):
        result = future.result()
        progress['resources'].append(result)
        if not result['ok']:
            progress['failures'].append(result)
        count = len(progress['resources'])
        if count % 20 == 0 or count == len(futures):
            progress['completed_resource_count'] = count
            progress['verified_bytes'] = sum(x.get('bytes', 0) for x in progress['resources'] if x['ok'])
            save()
            print(json.dumps({'completed': count, 'total': len(futures), 'failures': len(progress['failures']),
                              'verified_bytes': progress['verified_bytes'], 'seconds': round(time.monotonic() - start)}), flush=True)
progress['resources'].sort(key=lambda x: x['resource_path'])
progress['stage'] = 'parse' if not progress['failures'] else 'download'
progress['status'] = 'running' if not progress['failures'] else 'failed'
progress['next_action'] = 'parse' if not progress['failures'] else 'resume'
save()
