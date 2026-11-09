"""Real cloud + local bare Git end-to-end test of normal push/pull.

Creates only synthetic content in an isolated temporary directory below work/.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
AGENT = Path(__file__).with_name('baidu_lfs_agent.py')


def git(folder, *args, env=None):
    r = subprocess.run(['git', *args], cwd=folder, env=env, text=True,
                       capture_output=True, encoding='utf8', errors='replace', timeout=180)
    if r.returncode:
        raise RuntimeError(f'git {args[0]} failed: {r.stderr[-4000:]}')
    return r.stdout.strip()


def setup(repo):
    git(repo, 'lfs', 'install', '--local', '--force')
    git(repo, 'config', 'lfs.customtransfer.baidu.path', sys.executable)
    git(repo, 'config', 'lfs.customtransfer.baidu.args', f'-B {AGENT.as_posix()}')
    git(repo, 'config', 'lfs.customtransfer.baidu.concurrent', 'false')
    git(repo, 'config', 'lfs.standalonetransferagent', 'baidu')
    if git(repo, 'config', '--get', 'lfs.standalonetransferagent') != 'baidu':
        raise RuntimeError('Agent not configured')


def main():
    base = ROOT / 'work/baidu-lfs-agent'
    base.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='git-integration-', dir=base) as tmp:
        folder = Path(tmp)
        git(folder, 'init', '--bare', '--initial-branch=main', str(folder/'bare.git'))
        git(folder, 'clone', str(folder/'bare.git'), 'sender')
        sender = folder/'sender'
        git(sender, 'config', 'user.name', 'Storage Test')
        git(sender, 'config', 'user.email', 'storage-test@example.invalid')
        setup(sender)
        git(sender, 'lfs', 'track', '*.bin')
        first = b'Foundry Git LFS Baidu integration v1\n' * 128
        asset = sender/'asset.bin'
        asset.write_bytes(first)
        git(sender, 'add', '.gitattributes', 'asset.bin')
        git(sender, 'commit', '-m', 'first synthetic asset')
        git(sender, 'push', 'origin', 'main')
        marker = git(sender, 'show', 'HEAD:asset.bin')
        if hashlib.sha256(first).hexdigest() not in marker:
            raise RuntimeError('LFS pointer was not committed')
        env = dict(os.environ, GIT_LFS_SKIP_SMUDGE='1')
        git(folder, 'clone', str(folder/'bare.git'), 'receiver', env=env)
        receiver = folder/'receiver'
        setup(receiver)
        # A normal pull must hydrate this changed asset through the adapter.
        second = b'Foundry Git LFS Baidu integration v2\n' * 128
        asset.write_bytes(second)
        git(sender, 'add', 'asset.bin')
        git(sender, 'commit', '-m', 'update synthetic asset')
        git(sender, 'push', 'origin', 'main')
        git(receiver, 'pull', '--ff-only')
        restored = (receiver/'asset.bin').read_bytes()
        if restored != second:
            raise RuntimeError('Normal pull did not hydrate asset through Baidu')
        if git(receiver, 'status', '--porcelain'):
            raise RuntimeError('Receiver not clean after normal pull')
        # An existing object lives only inside the published 55-pack snapshot.
        # Confirm the normal Git pull path can hydrate it too.
        old = ROOT / 'docs/reviews/fish-reference-comparison-20261105.pdf'
        old_oid = hashlib.sha256(old.read_bytes()).hexdigest()
        published = json.loads((ROOT/'docs/storage/baidu-lfs-20261109/manifest.json').read_text(encoding='utf8'))
        if old_oid not in published['objects']:
            raise RuntimeError('Legacy test object absent from published snapshot')
        git(sender, 'lfs', 'track', '*.pdf')
        shutil.copyfile(old, sender/'legacy.pdf')
        git(sender, 'add', '.gitattributes', 'legacy.pdf')
        git(sender, 'commit', '-m', 'reference existing snapshot object')
        empty_hooks = folder/'empty-hooks';empty_hooks.mkdir()
        # Test-only: emulate a ref whose object was backed up before adapter
        # installation. The real Git push path was tested above.
        git(sender, '-c', f'core.hooksPath={empty_hooks.as_posix()}', 'push', 'origin', 'main')
        git(receiver, 'pull', '--ff-only')
        if hashlib.sha256((receiver/'legacy.pdf').read_bytes()).hexdigest() != old_oid:
            raise RuntimeError('Normal pull did not hydrate legacy snapshot object')
        before = git(folder/'bare.git', 'rev-parse', 'refs/heads/main')
        # A broken transfer command must fail pre-push and leave the Git ref
        # pointing to the old commit, despite a new local LFS pointer.
        asset.write_bytes(b'Foundry Git LFS Baidu integration failure gate\n' * 128)
        git(sender, 'add', 'asset.bin')
        git(sender, 'commit', '-m', 'third synthetic asset')
        git(sender, 'config', 'lfs.customtransfer.baidu.path', str(folder/'missing-agent.exe'))
        failed = subprocess.run(['git', 'push', 'origin', 'main'], cwd=sender,
                                capture_output=True, text=True, timeout=60)
        if failed.returncode == 0 or git(folder/'bare.git', 'rev-parse', 'refs/heads/main') != before:
            raise RuntimeError('Failed adapter did not block Git push')
        print(json.dumps({'ok':True,'normal_push_upload':True,'normal_pull_download':True,
                          'first_sha256':hashlib.sha256(first).hexdigest(),
                          'second_sha256':hashlib.sha256(second).hexdigest(),
                          'receiver_clean':True,'legacy_pack_pull':True,
                          'failed_transfer_blocked_push':True,
                          'external_git_remote':False}),flush=True)


if __name__=='__main__':main()
