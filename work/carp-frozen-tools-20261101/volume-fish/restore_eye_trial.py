"""Restore a frozen 106/107 eye trial into a new local project, without importing it.

Text is restored with LF (the archived byte convention), independently of Git's
Windows checkout setting. Binary sources are copied without transformation.
"""
import argparse
import hashlib
import json
from pathlib import Path


TEXT_SUFFIXES = {'.json', '.gd', '.gdshader', '.gdshaderinc', '.godot', '.tscn', '.txt'}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def frozen_bytes(path, expected=None):
    raw = path.read_bytes()
    if path.suffix in TEXT_SUFFIXES:
        raw = raw.replace(b'\r\n', b'\n')
    if expected and digest(raw) != expected:
        raise ValueError(f'Archive hash mismatch: {path}')
    return raw


def inside(root, relative):
    target = (root / relative).resolve()
    if not target.is_relative_to(root) or target == root:
        raise ValueError(f'Path outside destination: {relative}')
    return target


def restore(archive, output, repository):
    manifest = json.loads((archive / 'rebuild-inputs.manifest.json').read_text(encoding='utf8'))
    if output.exists():
        raise ValueError(f'Destination must not exist: {output}')
    if not output.is_relative_to(repository / 'projects'):
        raise ValueError('Destination must be a new project inside repository/projects')
    prepared = {}
    for source_root in [repository / manifest['base_fixture'], archive / 'runtime-overlay']:
        for path in sorted(source_root.rglob('*')):
            if not path.is_file() or 'import-settings' in path.relative_to(source_root).parts:
                continue
            relative = path.relative_to(source_root)
            prepared[relative] = frozen_bytes(path)
    model = manifest['model']
    prepared[Path('assets/models/fish') / (manifest['species'] + '.glb')] = frozen_bytes(
        repository / model['tracked_source'], model['sha256'])
    number = '106' if manifest['species'] == 'black_seabream' else '107'
    for entry in manifest['frozen_data']:
        relative = Path('assets/models/fish/motion') / ('eye-' + number) / Path(entry['path']).name
        prepared[relative] = frozen_bytes(archive / entry['path'], entry['sha256'])
    for entry in manifest['import_settings']['files']:
        prepared[Path(entry['restore_relative_path'])] = frozen_bytes(archive / entry['archive_path'], entry['sha256'])
    # Validate every path and input before creating any files.
    targets = [(inside(output, relative), raw) for relative, raw in prepared.items()]
    for target, raw in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    result = {
        'schema_version': 1, 'ok': True, 'command': 'fish.restore-eye-trial',
        'status': 'done', 'next_action': 'human_review',
        'inputs': {'archive': str(archive)}, 'outputs': [str(output)],
        'summary': {'files': len(targets), 'model_sha256': model['sha256'],
                    'text_newlines': 'LF', 'godot_import_executed': False,
                    'gpu_validation_performed': False, 'whole_fish_accepted': False},
        'failures': [],
    }
    (output / 'restoration.validation.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    repository = Path(__file__).resolve().parents[3]
    print(json.dumps(restore(args.archive.resolve(), args.output.resolve(), repository)))


if __name__ == '__main__':
    main()
