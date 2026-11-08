"""Local restoration/path/corruption checks. No network or real credentials."""
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('snapshot', Path(__file__).with_name('baidu_lfs_snapshot.py'))
snapshot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snapshot)


class RestoreTests(unittest.TestCase):
    def setUp(self):
        # Only test-owned synthetic files, under the workspace (never drive root).
        staging = snapshot.ROOT / 'work/baidu-lfs-20261109'
        staging.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='restore-test-', dir=staging)
        self.root = Path(self.temp.name)
        self.review = self.root / 'review'
        self.work = self.root / 'work/staging'
        (self.work / 'receive').mkdir(parents=True)
        self.data = b'\x00\xfforiginal binary\r\n' * 9
        self.oid = hashlib.sha256(self.data).hexdigest()
        packs = []
        # One logical file split over two packs, plus an alias in another repo.
        for index, (offset, data) in enumerate([(0, self.data[:17]), (17, self.data[17:])]):
            member = {'oid': self.oid, 'offset': offset, 'bytes': len(data),
                      'sha256': hashlib.sha256(data).hexdigest(), 'name': f'{self.oid}/{offset:012d}'}
            path = self.work / 'receive' / f'{index:04d}.tar'
            with tarfile.open(path, 'w', format=tarfile.USTAR_FORMAT) as tar:
                info = tarfile.TarInfo(member['name']); info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
            packs.append({'index': index, 'sha256': snapshot.sha(path), 'bytes': path.stat().st_size,
                          'members': [member], 'remote': 'synthetic-not-used'})
        self.m = {'objects': {self.oid: {'bytes': len(self.data)}}, 'packs': packs, 'path_count': 2,
                  'repositories': {name: {'files': [{'path': 'assets/fish.bin', 'oid': self.oid, 'bytes': len(self.data)}]}
                                   for name in ['foundry', 'fishing-2d']}}
        snapshot.save(self.review / 'manifest.json', self.m)
        snapshot.save(self.review / 'publication.json', {'sha256': snapshot.sha(self.review / 'manifest.json')})
        self.patches = [patch.object(snapshot, 'ROOT', self.root), patch.object(snapshot, 'REVIEW', self.review),
                        patch.object(snapshot, 'WORK', self.work), patch.object(snapshot, 'authenticated'),
                        patch.object(snapshot, 'api', side_effect=AssertionError('No network allowed in test'))]
        for p in self.patches: p.start()

    def tearDown(self):
        for p in reversed(self.patches): p.stop()
        self.temp.cleanup()

    def test_restore_chunked_file_and_alias_exact_bytes(self):
        snapshot.restore('fresh')
        for name in ['foundry', 'fishing-2d']:
            self.assertEqual((self.root / 'work/fresh' / name / 'assets/fish.bin').read_bytes(), self.data)
        with self.assertRaisesRegex(RuntimeError, 'exists'):
            snapshot.restore('fresh')

    def test_reject_path_escape_before_network_or_write(self):
        with self.assertRaisesRegex(ValueError, 'outside'):
            snapshot.restore('../escape')

    def test_reject_corrupt_chunk_and_missing_object(self):
        m = copy.deepcopy(self.m)
        m['packs'][0]['members'][0]['sha256'] = '0' * 64
        with self.assertRaisesRegex(RuntimeError, 'Chunk mismatch'):
            snapshot.verify_content(m, self.work / 'receive')
        m = copy.deepcopy(self.m)
        m['objects']['f' * 64] = {'bytes': 1}
        with self.assertRaisesRegex(RuntimeError, 'coverage mismatch'):
            snapshot.verify_content(m, self.work / 'receive')


if __name__ == '__main__':
    unittest.main()
