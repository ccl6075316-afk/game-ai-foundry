"""Check that installed fish contain no independent lip meshes."""
import argparse
import hashlib
import json
import struct
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect(game: Path):
    config = game / 'assets/models/fish/motion/mouth-repair139.json'
    profiles = json.loads(config.read_text(encoding='utf8'))['profiles']
    failures = [f'{species}: active lips resource' for species, profile in profiles.items()
                if 'lips' in profile]
    model_files = sorted((game / 'assets/models/fish').glob('*.glb'))
    for path in model_files:
        data = path.read_bytes()
        if data[:4] != b'glTF' or struct.unpack_from('<I', data, 8)[0] != len(data):
            failures.append(f'{path.name}: invalid GLB header')
            continue
        json_length = struct.unpack_from('<I', data, 12)[0]
        document = json.loads(data[20:20 + json_length])
        if any(node.get('name') == 'Source_lips139' for node in document.get('nodes', [])):
            failures.append(f'{path.name}: embedded Source_lips139')
    return {
        'kind': 'fish_independent_lip_retirement_validation',
        'ok': not failures,
        'config_sha256': sha(config),
        'model_count': len(model_files),
        'mouth_profile_count': len(profiles),
        'whale_shark_glb_sha256': sha(game / 'assets/models/fish/whale_shark.glb'),
        'independent_lip_nodes': 0 if not failures else None,
        'failures': failures,
        'scope': 'Static config and final GLB inventory. Runtime binding and visual review are separate.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = inspect(args.game.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps(report, ensure_ascii=False))
    raise SystemExit(0 if report['ok'] else 1)


if __name__ == '__main__':
    main()
