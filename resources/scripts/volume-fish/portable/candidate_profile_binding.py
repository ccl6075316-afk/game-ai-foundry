"""Reject geometry-profile drift across material, roots and review settings."""
from pathlib import Path
from parts import read,sha
from fish_asset_spec import ROOT,require

def check_profiles(author_file,root_plan_file,review_file):
 author=read(author_file);roots=read(root_plan_file);review=read(review_file)
 require(len(roots['items'])==1,'One own-species root plan required')
 item=roots['items'][0];profile=(ROOT/author['profile']).resolve()
 require(profile==(ROOT/review['geometry_profile']).resolve()==(ROOT/item['profile']).resolve(),'Geometry profile differs across author, full roots and review')
 require(sha(profile)==item['profile_sha256'],'Stale geometry profile behind full root plan')
 actual=read(profile);require(actual['species']==item['species'],'Profile/root species mismatch')
 require(author['body']==review['body']==item['body'],'Profile binding body identity mismatch')
 return {'ok':True,'kind':'candidate_geometry_profile_binding','species':item['species'],'body':item['body'],'profile':{'path':str(profile),'sha256':sha(profile)},'scope':'Consistent explicit profile only; does not select the right revision, inspect anatomy or grant acceptance.'}
