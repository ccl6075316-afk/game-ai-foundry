"""Recreate source-bound analysis inputs inside repository work/, never run APK."""
from pathlib import Path
import hashlib
import json
import zipfile

REPO = next(p for p in Path(__file__).resolve().parents if (p / 'cli/gamefactory.py').is_file())
DB = REPO / 'resources/fish-database'
APK = DB / 'artifacts/fishing-master-xiaomi-20260814/fishing-xiaomi-1.0.0.265409.apk'
WORK = REPO / 'work/fish-motion-reconstruction-20261102'
assert WORK.resolve().is_relative_to((REPO / 'work').resolve())

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

if __name__ == '__main__':
    assert digest(APK) == '8a6f23099eb334f2d4a7a7a02058c1cf021551dd7e892cbf426c4c511b5ac7b7'
    WORK.mkdir(parents=True, exist_ok=True)
    inputs = [
        ('lib/arm64-v8a/libil2cpp.so', 'libil2cpp.so', '83ea8e5b7a353991f3ca10d0a3e16cfa9f734273e7e35596b5901a2b4b79757f'),
        ('assets/bin/Data/Managed/Metadata/global-metadata.dat', 'global-metadata.dat', 'b2ec6ff11b15fd55017007cfec852344e78d3b3a13be78d8f5140c78b678d454'),
    ]
    result = []
    with zipfile.ZipFile(APK) as archive:
        for entry, name, expected in inputs:
            target = WORK / name
            if not target.exists():
                data = archive.read(entry)
                assert hashlib.sha256(data).hexdigest() == expected
                with target.open('xb') as f:
                    f.write(data)
            assert digest(target) == expected, 'Existing work input has wrong SHA256: ' + name
            result.append({'path': str(target.relative_to(REPO)), 'sha256': expected, 'bytes': target.stat().st_size})
    print(json.dumps({'ok': True, 'inputs': result}, indent=2))
