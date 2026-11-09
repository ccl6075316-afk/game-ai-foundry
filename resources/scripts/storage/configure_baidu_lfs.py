"""Configure both local Git checkouts to use the verified Baidu LFS adapter.

Dry-run by default. Never stores credentials or alters tracked .lfsconfig.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / 'resources/scripts/storage/baidu_lfs_agent.py'
REPOS = [ROOT, ROOT / 'projects/fishing-2d']


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True, encoding='utf8').strip()


def preflight(repo):
    if Path(git(repo, 'rev-parse', '--show-toplevel')).resolve() != repo.resolve():
        raise RuntimeError(f'Unexpected Git root: {repo}')
    if git(repo, 'status', '--porcelain', '--untracked-files=no'):
        raise RuntimeError(f'Tracked changes in {repo}; finish them before backend setup')
    hook_dir = git(repo, 'rev-parse', '--git-path', 'hooks')
    custom = subprocess.run(['git', '-C', str(repo), 'config', '--local', '--get', 'core.hooksPath'],
                            capture_output=True, text=True, encoding='utf8')
    if custom.returncode == 0:
        hook_dir = custom.stdout.strip()
    hook = Path(hook_dir)
    if not hook.is_absolute():
        hook = repo / hook
    prepush = hook / 'pre-push'
    if not prepush.is_file() or 'git lfs pre-push' not in prepush.read_text(encoding='utf8'):
        raise RuntimeError(f'Missing Git LFS pre-push hook: {prepush}')
    return {'repo': str(repo), 'hook': str(prepush), 'head': git(repo, 'rev-parse', '--short', 'HEAD')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not SCRIPT.is_file() or not Path(sys.executable).is_file():
        raise RuntimeError('Agent or Python executable missing')
    checked = [preflight(repo) for repo in REPOS]
    if args.apply:
        for repo in REPOS:
            # Replaces only local LFS filter settings; --skip-repo preserves hooks.
            git(repo, 'lfs', 'install', '--local', '--force', '--skip-repo')
            options = {
                'lfs.customtransfer.baidu.path': str(Path(sys.executable).resolve()),
                'lfs.customtransfer.baidu.args': '-B "' + SCRIPT.as_posix() + '"',
                'lfs.customtransfer.baidu.concurrent': 'false',
                'lfs.standalonetransferagent': 'baidu',
            }
            for key, value in options.items():
                git(repo, 'config', '--local', key, value)
            if git(repo, 'config', '--local', '--get', 'lfs.standalonetransferagent') != 'baidu':
                raise RuntimeError(f'Configuration did not persist: {repo}')
    print(json.dumps({'ok': True, 'apply': args.apply, 'checkouts': checked,
                      'adapter': str(SCRIPT), 'credentials_written': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
