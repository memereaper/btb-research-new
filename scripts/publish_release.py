#!/usr/bin/env python3
"""Create a versioned publication bundle, with no live website changes."""
import json, shutil, sys, tempfile, os
from pathlib import Path
from build_historical import ROOT, digest, verify

def publish(root=ROOT):
    sid = json.loads((root/'warehouse/current.json').read_text())['snapshot_id']
    source = root/'warehouse/snapshots'/sid
    manifest = verify(source)
    releases = root/'releases'; releases.mkdir(exist_ok=True)
    target = releases/sid
    if not target.exists():
        temp = Path(tempfile.mkdtemp(prefix='.publishing-',dir=releases))
        try:
            for name in ['core','investigation']: shutil.copytree(source/name,temp/name)
            for name in ['manifest.json','validation.json']: shutil.copy2(source/name,temp/name)
            shutil.copy2(ROOT/'investigations/where-bills-go-to-die/methodology.md',temp/'METHODS.md')
            shutil.copy2(source/'raw/data/README.md',temp/'SOURCE_NOTES.md')
            shutil.copy2(source/'raw/data/118_published_reconciliation.csv',temp/'118_published_reconciliation.csv')
            package = {'snapshot_id':sid,'files':[{'path':str(p.relative_to(temp)),'sha256':digest(p),'bytes':p.stat().st_size} for p in sorted(temp.rglob('*')) if p.is_file()]}
            (temp/'package.json').write_text(json.dumps(package,indent=2)+'\n')
            os.rename(temp,target)
        except BaseException:
            shutil.rmtree(temp,ignore_errors=True); raise
    package = json.loads((target/'package.json').read_text())
    for entry in package['files']:
        if digest(target/entry['path']) != entry['sha256']: raise ValueError('Damaged release: '+entry['path'])
    archive = releases/(sid+'.zip')
    if not archive.exists():
        temporary = shutil.make_archive(str(releases/('.'+sid)), 'zip', target)
        os.replace(temporary,archive)
    print(archive)
    return target
if __name__ == '__main__': publish()
