"""Verify exact retained evidence bytes, optionally restore into an empty tree."""
import argparse,gzip,hashlib,json,shutil,tarfile
from pathlib import Path,PurePosixPath

def safe(root,name):
    rel=PurePosixPath(name)
    if rel.is_absolute() or '..' in rel.parts or ':' in name or '\\' in name:
        raise ValueError('Unsafe archive path: '+name)
    target=root.joinpath(*rel.parts).resolve()
    if not target.is_relative_to(root):raise ValueError('Escaping archive path: '+name)
    return target

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--archive',type=Path,required=True)
    ap.add_argument('--index',type=Path,required=True)
    ap.add_argument('--root',type=Path)
    ap.add_argument('--verify-only',action='store_true')
    ap.add_argument('--json',action='store_true')
    args=ap.parse_args()
    if not args.verify_only and args.root is None:ap.error('--root required for restoration')
    opener=gzip.open if args.index.suffix=='.gz' else open
    with opener(args.index,'rt',encoding='utf8') as f:rows=json.load(f)
    root=(args.root or Path.cwd()).resolve();members={}
    for row in rows:
        safe(root,row['member']);safe(root,row.get('restore_path',row['member']))
        previous=members.setdefault(row['member'],row)
        if (previous['bytes'],previous['sha256'])!=(row['bytes'],row['sha256']):
            raise ValueError('Conflicting index aliases')
    if not args.verify_only and root.exists() and any(root.iterdir()):
        raise ValueError('Restoration requires an empty destination; existing work is never overwritten')
    seen=set()
    with tarfile.open(args.archive,'r|gz') as archive:
        for entry in archive:
            if not entry.isfile() or entry.name not in members or entry.name in seen:
                raise ValueError('Unexpected archive entry: '+entry.name)
            row=members[entry.name];digest=hashlib.sha256();count=0
            with archive.extractfile(entry) as source:
                for block in iter(lambda:source.read(1024*1024),b''):
                    digest.update(block);count+=len(block)
            if count!=row['bytes'] or digest.hexdigest()!=row['sha256']:
                raise ValueError('Changed retained bytes: '+entry.name)
            seen.add(entry.name)
    if seen!=set(members):raise ValueError('Archive lacks indexed members')
    if not args.verify_only:
        root.mkdir(parents=True,exist_ok=True)
        with tarfile.open(args.archive,'r|gz') as archive:
            for entry in archive:
                target=safe(root,entry.name);target.parent.mkdir(parents=True,exist_ok=True)
                with archive.extractfile(entry) as source,target.open('xb') as output:shutil.copyfileobj(source,output)
        for row in rows:
            target=safe(root,row.get('restore_path',row['member']));source=safe(root,row['member'])
            if target!=source:
                target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    print(json.dumps(dict(ok=True,archive=str(args.archive.resolve()),unique_members=len(seen),original_files=len(rows),restored=not args.verify_only),ensure_ascii=False))

if __name__=='__main__':main()
