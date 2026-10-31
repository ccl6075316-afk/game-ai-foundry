"""Whole-fish triangle limits from the user's 2026-10-31 display-length rule.

Centimeters are configured display length, not a species maximum, tank size,
bounding sphere, image dimensions or an invitation to increase an accepted mesh.
"""
import math

POLICY_ID = 'user-display-length-20261031'

def triangle_policy(real_length_cm):
    if type(real_length_cm) not in (int,float) or not math.isfinite(real_length_cm) or real_length_cm<=0:
        raise ValueError('Positive finite configured display length in centimeters required')
    preferred,hard=(7500,8000) if real_length_cm>600 else (5500,6000) if real_length_cm>300 else (3500,4000) if real_length_cm>120 else (1500,2000)
    return {'policy_id':POLICY_ID,'real_length_cm':real_length_cm,'preferred_triangles':preferred,'hard_triangles':hard}

def check_triangle_budget(triangles,real_length_cm,declared_hard=None):
    policy=triangle_policy(real_length_cm)
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
