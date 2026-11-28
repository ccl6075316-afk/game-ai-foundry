"""Whole-fish & marine-fauna LOD0 triangle limits and 50k-entity LOD tier targets (2026-11-28).

Budgets combine two independent axes and take the higher applicable tier:
1. Configured display length in centimeters (not species max or tank size).
2. Morphological complexity group (`anatomical_group`):
   - `standard_lateral`: classic laterally compressed bony fish (main 50k schooling stock)
   - `shark`: cartilaginous sharks (5 gill slits, thick opaque fins, feeding jaws)
   - `dorsal_complex`: dorsal/ventral-dominant or wide-wing/shelled marine fauna
     (sea turtles, rays, mantas, flatfish, lionfish, seahorses)
   - `multi_limb`: multi-tentacle / multi-legged cephalopods & crustaceans
     (octopuses, squids, cuttlefish, lobsters, crabs, jellyfish)
"""
import math

POLICY_ID = 'user-lod0-50k-morphology-20261128'
SHARK_POLICY_ID = 'user-lod0-shark-20261128'
DORSAL_POLICY_ID = 'user-lod0-dorsal-complex-20261128'
MULTI_LIMB_POLICY_ID = 'user-lod0-multi-limb-20261128'

SHARK_SPECIES = frozenset({
    'blacktip_reef_shark', 'scalloped_hammerhead', 'great_hammerhead',
    'smooth_hammerhead', 'whale_shark',
})
DORSAL_COMPLEX_SPECIES = frozenset({
    'loggerhead', 'loggerhead_sea_turtle', 'skye_manta',
})
MULTI_LIMB_SPECIES = frozenset()
VALID_GROUPS = frozenset({'standard_lateral', 'shark', 'dorsal_complex', 'multi_limb'})

# Tier index: 0 = <=120cm standard, 1 = 120-300cm / shark / dorsal_complex, 2 = 300-600cm / multi_limb, 3 = >600cm
_LENGTH_TIERS = (
    (4000, 5000),
    (6500, 8000),
    (8500, 10000),
    (12000, 15000),
)

_LOD_TARGETS_BY_GROUP_AND_TIER = {
    'standard_lateral': (
        {'lod1': (400, 600), 'lod2': (120, 160), 'lod3': (32, 64)},
        {'lod1': (800, 1200), 'lod2': (250, 350), 'lod3': (64, 96)},
        {'lod1': (1500, 2500), 'lod2': (450, 700), 'lod3': (80, 128)},
        {'lod1': (3000, 4000), 'lod2': (900, 1200), 'lod3': (160, 240)},
    ),
    'shark': (
        {'lod1': (800, 1200), 'lod2': (250, 350), 'lod3': (64, 96)},
        {'lod1': (800, 1200), 'lod2': (250, 350), 'lod3': (64, 96)},
        {'lod1': (1500, 2500), 'lod2': (450, 700), 'lod3': (80, 128)},
        {'lod1': (3000, 4000), 'lod2': (900, 1200), 'lod3': (160, 240)},
    ),
    'dorsal_complex': (
        {'lod1': (1000, 1600), 'lod2': (300, 500), 'lod3': (96, 140)},
        {'lod1': (1000, 1600), 'lod2': (300, 500), 'lod3': (96, 140)},
        {'lod1': (1600, 2500), 'lod2': (500, 750), 'lod3': (110, 160)},
        {'lod1': (3000, 4000), 'lod2': (900, 1200), 'lod3': (160, 240)},
    ),
    'multi_limb': (
        {'lod1': (1500, 2400), 'lod2': (500, 800), 'lod3': (150, 220)},
        {'lod1': (1500, 2400), 'lod2': (500, 800), 'lod3': (150, 220)},
        {'lod1': (1500, 2400), 'lod2': (500, 800), 'lod3': (150, 220)},
        {'lod1': (3000, 4000), 'lod2': (900, 1200), 'lod3': (180, 260)},
    ),
}


def _resolve_group(species, anatomical_group):
    if anatomical_group is not None:
        if anatomical_group not in VALID_GROUPS:
            raise ValueError(f'Unknown anatomical_group: {anatomical_group!r}. Expected one of {sorted(VALID_GROUPS)}')
        return anatomical_group
    if species in SHARK_SPECIES:
        return 'shark'
    if species in DORSAL_COMPLEX_SPECIES:
        return 'dorsal_complex'
    if species in MULTI_LIMB_SPECIES:
        return 'multi_limb'
    return 'standard_lateral'


def _length_tier_index(real_length_cm):
    if real_length_cm > 600:
        return 3
    if real_length_cm > 300:
        return 2
    if real_length_cm > 120:
        return 1
    return 0


def triangle_policy(real_length_cm, *, species=None, anatomical_group=None):
    if type(real_length_cm) not in (int, float) or not math.isfinite(real_length_cm) or real_length_cm <= 0:
        raise ValueError('Positive finite configured display length in centimeters required')
    group = _resolve_group(species, anatomical_group)
    min_tier = {'standard_lateral': 0, 'shark': 1, 'dorsal_complex': 1, 'multi_limb': 2}[group]
    tier = max(_length_tier_index(real_length_cm), min_tier)
    preferred, hard = _LENGTH_TIERS[tier]
    policy_id = {
        'standard_lateral': POLICY_ID,
        'shark': SHARK_POLICY_ID,
        'dorsal_complex': DORSAL_POLICY_ID,
        'multi_limb': MULTI_LIMB_POLICY_ID,
    }[group]
    return {
        'policy_id': policy_id,
        'real_length_cm': real_length_cm,
        'preferred_triangles': preferred,
        'hard_triangles': hard,
        'lod_targets': _LOD_TARGETS_BY_GROUP_AND_TIER[group][tier],
        'anatomical_group': group,
        'species': species,
    }


def check_triangle_budget(triangles, real_length_cm, declared_hard=None, *, species=None, anatomical_group=None):
    policy = triangle_policy(real_length_cm, species=species, anatomical_group=anatomical_group)
    if type(triangles) is not int or triangles < 0:
        raise ValueError('Nonnegative integer whole-fish triangle count required')
    hard = policy['hard_triangles']
    if declared_hard is not None:
        if type(declared_hard) is not int or not 0 < declared_hard <= hard:
            raise ValueError('Declared budget exceeds display-length hard limit: ' + str(hard))
        hard = declared_hard
    if triangles > hard:
        raise ValueError(f'Whole-fish budget exceeded: {triangles} > {hard} at display length {real_length_cm}cm ({policy["anatomical_group"]})')
    return {
        'ok': True,
        **policy,
        'triangles': triangles,
        'effective_hard_triangles': hard,
        'preferred_met': triangles <= policy['preferred_triangles'],
        'scope': 'LOD0 whole-entity triangle count (body, jaws/oral, complete fins/limbs/shells and 3D eyes). Technical count only; visual, anatomical, underwater optics and cold-export gates apply separately.',
    }
