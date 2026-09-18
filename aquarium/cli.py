from __future__ import annotations
import argparse
import json
import shutil
import sqlite3
from pathlib import Path
from .catalog import ROOT, load_catalog
from .sprites import ReferenceBackend, QwenBackend, DiffSynthBackend, run_batch, atomic_json

def export_extension(items, directory):
    assets = ROOT/'extension/assets'; assets.mkdir(exist_ok=True)
    job_path = Path(directory)/'jobs.sqlite'
    jobs = sqlite3.connect(job_path) if job_path.exists() else None
    catalog = []
    for i in items:
        if not i['eligible']:
            continue
        source = Path(directory)/(i['id']+'.png')
        record = {k: i[k] for k in ('id','name','scientific_name','kind','facts','issues','url')}
        record['sprite'] = None
        state = jobs.execute('SELECT status,fingerprint FROM jobs WHERE id=?',(i['id'],)).fetchone() if jobs else None
        metadata = json.loads(source.with_suffix('.json').read_text()) if source.with_suffix('.json').exists() else {}
        if source.exists() and state and state == ('done',metadata.get('fingerprint')):
            shutil.copyfile(source, assets/source.name)
            record['sprite'] = 'assets/'+source.name
        catalog.append(record)
    atomic_json(assets/'catalog.json', catalog)
    if jobs: jobs.close()
    return len(catalog)

def main(argv=None):
    p=argparse.ArgumentParser(description='Pipeline Aquário')
    p.add_argument('--dataset', type=Path, default=ROOT/'kauar_peixes.json')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('audit'); sub.add_parser('index')
    b=sub.add_parser('sprites'); b.add_argument('--backend',choices=['reference','qwen','diffsynth'],default='reference'); b.add_argument('--ids',nargs='+'); b.add_argument('--limit',type=int,default=3); b.add_argument('--all',action='store_true'); b.add_argument('--lora'); b.add_argument('--anchor',action='append',default=[]); b.add_argument('--revision'); b.add_argument('--out',type=Path,default=ROOT/'data/generated')
    e=sub.add_parser('export'); e.add_argument('--sprites',type=Path,default=ROOT/'data/generated')
    a=p.parse_args(argv); items=load_catalog(a.dataset)
    if a.command=='audit':
        result={'total':len(items),'eligible':sum(i['eligible'] for i in items),'issues':[{k:i[k] for k in ('id','name','issues')} for i in items if i['issues']]}; atomic_json(ROOT/'data/audit.json',result);print({k:v for k,v in result.items() if k!='issues'})
    elif a.command=='index':
        from .rag import SpeciesIndex
        print('Indexed',SpeciesIndex().build(items))
    elif a.command=='export':
        print('Exported',export_extension(items,a.sprites))
    else:
        if a.ids:
            wanted=set(a.ids);items=[i for i in items if i['id'] in wanted]
            if {i['id'] for i in items} != wanted: p.error('ID desconhecido')
        elif not a.all:
            smoke=json.loads((ROOT/'config/smoke.json').read_text()); ids={i['id'] for i in smoke};items=[i for i in items if i['id'] in ids][:a.limit]
        if a.all and a.backend=='reference': p.error('Lote completo requer --backend qwen; referências só cobrem o smoke test')
        backend=ReferenceBackend(ROOT/'data/references') if a.backend=='reference' else (DiffSynthBackend if a.backend=='diffsynth' else QwenBackend)(a.lora,a.anchor,a.revision)
        report=run_batch(items,backend,a.out);print(json.dumps(report,indent=2));raise SystemExit(1 if report['failed'] else 0)

if __name__=='__main__':main()
