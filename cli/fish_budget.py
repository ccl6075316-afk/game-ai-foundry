"""Whole-fish triangle limits from the user's 2026-10-31 display-length rule.

Centimeters are configured display length, not a species maximum, tank size,
bounding sphere, image dimensions or an invitation to increase an accepted mesh.
"""
import math

POLICY_ID = 'user-display-length-20261031'
SHARK_POLICY_ID = 'user-shark-minimum-tier-20261101'
SHARK_SPECIES = frozenset({'blacktip_reef_shark','scalloped_hammerhead','great_hammerhead','smooth_hammerhead','whale_shark'})

def triangle_policy(real_length_cm, *, species=None, anatomical_group=None):
    if type(real_length_cm) not in (int,float) or not math.isfinite(real_length_cm) or real_length_cm<=0:
        raise ValueError('Positive finite configured display length in centimeters required')
    preferred,hard=(7500,8000) if real_length_cm>600 else (5500,6000) if real_length_cm>300 else (3500,4000) if real_length_cm>120 else (1500,2000)
    shark=anatomical_group=='shark' or species in SHARK_SPECIES
    if shark:preferred,hard=max(preferred,3500),max(hard,4000)
    policy_id = SHARK_POLICY_ID if shark else POLICY_ID
    if species == 'whale_shark' and real_length_cm == 800:
        hard = 10000
        policy_id = 'user-whale-shark-800cm-20261106'
    return {'policy_id':policy_id,'real_length_cm':real_length_cm,'preferred_triangles':preferred,'hard_triangles':hard,'anatomical_group':'shark' if shark else anatomical_group,'species':species}

def check_triangle_budget(triangles,real_length_cm,declared_hard=None, *, species=None, anatomical_group=None):
    policy=triangle_policy(real_length_cm,species=species,anatomical_group=anatomical_group)
    if type(triangles) is not int or triangles<0:
        raise ValueError('Nonnegative integer whole-fish triangle count required')
    hard=policy['hard_triangles']
    if declared_hard is not None:
        if type(declared_hard) is not int or not 0<declared_hard<=hard:
            raise ValueError('Declared budget exceeds display-length hard limit: '+str(hard))
        hard=declared_hard
    if triangles>hard:
        raise ValueError(f'Whole-fish budget exceeded: {triangles} > {hard} at display length {real_length_cm}cm')
    return {'ok':True,**policy,'triangles':triangles,'effective_hard_triangles':hard,'preferred_met':triangles<=policy['preferred_triangles'],'scope':'All actual body, mouth/oral/jaws, complete fin faces/edges and extra layers. Technical count only; no visual/anatomical acceptance.'}
