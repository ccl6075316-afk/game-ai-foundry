"""Restore a retained three-fish review archive over the formal game in temp.

Example: --archive <mouth-round-122/candidate> --game <fishing-2d/game>
Writes a temporary game, never edits the formal game. Run through Foundry play.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--game',type=Path,required=True)
    a=p.parse_args()
    archive=a.archive.resolve();game=a.game.resolve()
    receipt=json.loads((archive/'archive.validation.json').read_text())
    assert (game/'project.godot').is_file()
    assert receipt['ok'] and receipt['runtime_scripts_frozen']
    for name,digest in receipt['archive_files_sha256'].items():
        assert hashlib.sha256((archive/name).read_bytes()).hexdigest()==digest, name
    for species,digest in receipt['models'].items():
        assert hashlib.sha256((archive/f'models/{species}.glb').read_bytes()).hexdigest()==digest
    target=Path(tempfile.mkdtemp(prefix='foundry-fish-review-'))/'game'
    shutil.copytree(game,target,ignore=shutil.ignore_patterns('.godot','.git','bin','obj','*.import','*.uid'))
    for species in receipt['models']:
        shutil.copy2(archive/f'models/{species}.glb',target/f'assets/models/fish/{species}.glb')
    for file in (archive/'motion').glob('*.json'):
        shutil.copy2(file,target/'assets/models/fish/motion'/file.name)
    shutil.copytree(archive/'scripts/aquarium',target/'scripts/aquarium',dirs_exist_ok=True)
    species=set(json.loads((archive/'motion/motion.json').read_text())['profiles'])
    for file in (target/'assets/models/fish').glob('*.glb'):
        if file.stem not in species:file.unlink()
    assert {f.stem for f in (target/'assets/models/fish').glob('*.glb')}==species
    print(json.dumps({'ok':True,'temporary_game':str(target),'cleanup_directory':str(target.parent),
                      'next_action':'Run Foundry play with temporary_game, then remove cleanup_directory after review.'},ensure_ascii=False))


if __name__=='__main__':main()
