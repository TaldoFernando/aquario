"""Prepare aligned input/target metadata for DiffSynth's image-edit trainer.
Targets are normalized teacher sprites enlarged NEAREST on white; split by
scientific species, so color variants cannot leak between train and validation.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from PIL import Image, ImageOps
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from aquarium.catalog import ROOT, load_catalog, fold
from aquarium.sprites import atomic_json

def prepare(dataset, generated, out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    groups={};provenance=[]
    for item in load_catalog(dataset):
        sid=item['id']; target=Path(generated)/(sid+'.png');source=ROOT/'data/sources'/(sid+'.png');meta=target.with_suffix('.json')
        if not target.exists() or not source.exists() or not meta.exists():continue
        info=json.loads(meta.read_text())
        if info['backend']!='teacher-reference':continue # do not recursively train on student output
        key=fold(item['scientific_name'] or item['name']); group=hashlib.sha256(key.encode()).hexdigest()
        folder=out/'images';folder.mkdir(exist_ok=True)
        photo=ImageOps.pad(Image.open(source).convert('RGB'),(768,768),color='white');photo.save(folder/(sid+'-input.png'))
        sprite=Image.open(target).convert('RGBA').resize((768,768),Image.Resampling.NEAREST)
        white=Image.new('RGBA',(768,768),'white');white.alpha_composite(sprite);white.convert('RGB').save(folder/(sid+'-target.png'))
        row={'image':f'images/{sid}-target.png','edit_image':[f'images/{sid}-input.png'],'prompt':info['prompt']}
        groups.setdefault(group,[]).append(row)
        provenance.append({'id':sid,'source_url':item['image_url'],'group':group,'generator':info['backend'],'source_sha256':info['source_sha256']})
    ordered=sorted(groups)
    val_groups=set(ordered[::5]) if len(ordered)>1 else set()
    train=[row for g,rows in groups.items() if g not in val_groups for row in rows]
    val=[row for g,rows in groups.items() if g in val_groups for row in rows]
    atomic_json(out/'train.json',train);atomic_json(out/'validation.json',val);atomic_json(out/'provenance.json',provenance)
    summary={'pairs':len(provenance),'species_groups':len(groups),'train':len(train),'validation':len(val),'training_ready':len(train)>=30 and len(val)>=5}
    atomic_json(out/'summary.json',summary);return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',type=Path,default=ROOT/'kauar_peixes.json');p.add_argument('--generated',type=Path,default=ROOT/'data/generated');p.add_argument('--out',type=Path,default=ROOT/'data/pairs');a=p.parse_args();print(json.dumps(prepare(a.dataset,a.generated,a.out),indent=2))
