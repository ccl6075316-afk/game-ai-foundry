"""Record current independent species parameters and full cap ownership."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--experiment', type=Path, required=True)
    args = parser.parse_args()
    experiment = args.experiment.resolve()
    manifest = read(experiment / 'manifest.json')
    for short, species in [('great', 'great_hammerhead'), ('smooth', 'smooth_hammerhead')]:
        base = experiment / short
        candidate = base / manifest['candidate_dirs'][species]
        config = read(base / 'preparation-r2/config.json')
        old = read(Path(config['art_profile']))
        authored = read(candidate / 'fin-authoring.json')
        fins = []
        for fin in old['fins']:
            fin = copy.deepcopy(fin)
            name = fin['name']
            parts = [row for row in authored['fins']
                     if row['name'] == name or row['name'].startswith(name + '_')]
            assert parts
            fin['root_attachment'] = {
                'method': 'complete_native_finite_body_subtraction_cap',
                'root_band': {
                    'kind': 'complete_native_cap_with_shared_finite_body_support',
                    'actual_meshes': [row['name'] for row in parts],
                    'root_ids_by_mesh': {row['name']: row['root_ids'] for row in parts},
                    'native_source_curves_px': {
                        row['name']: row['source_root_curve_px'] for row in parts},
                },
            }
            fins.append(fin)
        provenance = base / 'sources/source-provenance.json'
        if not provenance.exists():
            original = (ROOT / 'projects/fishing-2d/experiments/blender-fish'
                        / 'hammer-pair-121/accepted' / species / 'accepted.handoff.json')
            provenance.write_bytes(original.read_bytes())
        profile = {
            'schema_version': 1,
            'kind': 'own_art_hammerhead_rebuild_species_profile',
            'species': species,
            'scientific_name': config['scientific_name'],
            'real_length_cm': int(config['display_length_m'] * 100),
            'budget': {
                'preferred': 5500 if short == 'great' else 3500,
                'hard_limit': 6000 if short == 'great' else 4000,
                'actual': authored['whole_triangles'],
            },
            'head': {
                'span_over_display_length': config['target_head_span_over_length'],
                'own_front_art_thickness_over_span': config['head_projected_full_thickness_over_span'],
                'notes': 'Own source-art proportions; family foil/bridge method only, not biological measurements.',
            },
            'body': {
                'sections': config['body_sections_override'],
                'width_basis': 'Own fin-free anterior top-art measurements; own historical posterior artistic priors.',
            },
            'fins': fins,
            'accepted_source_provenance': str(provenance),
            'source_hashes': {role: sha(base / 'sources' / (role + '.png'))
                              for role in ['side', 'front', 'top', 'bottom']},
            'model_sha256': sha(candidate / 'fish.glb'),
            'source_authoring_sha256': sha(candidate / 'fin-authoring.json'),
            'user_visual_acceptance': False,
        }
        path = ROOT / 'resources/volume-fish' / (short + '-hammerhead-rebuild-20261105.profile.json')
        write(path, profile)
        write(base / 'volume.contract.json', {
            'profile': str(path),
            'tail_section': str(base / 'tail-section.validation.json'),
        })
        print(species, authored['whole_triangles'])

if __name__ == '__main__':
    main()
