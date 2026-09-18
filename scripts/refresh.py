"""Incremental end-to-end batch: smoke gate -> full catalog -> RAG -> export."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from aquarium.catalog import ROOT,load_catalog
from aquarium.sprites import QwenBackend,DiffSynthBackend,run_batch
from aquarium.rag import SpeciesIndex
from aquarium.cli import export_extension
p=argparse.ArgumentParser();p.add_argument('--dataset',type=Path,default=ROOT/'kauar_peixes.json');p.add_argument('--backend',choices=['qwen','diffsynth'],required=True);p.add_argument('--lora');p.add_argument('--out',type=Path,default=ROOT/'data/production');p.add_argument('--anchor',action='append',default=[]);p.add_argument('--revision');a=p.parse_args()
import torch
if not torch.cuda.is_available():p.error('Worker CUDA indisponível. Nenhum lote foi iniciado.')
backend=(DiffSynthBackend if a.backend=='diffsynth' else QwenBackend)(a.lora,a.anchor,a.revision)
items=load_catalog(a.dataset);smoke_ids={i['id'] for i in json.loads((ROOT/'config/smoke.json').read_text())}
smoke=[i for i in items if i['id'] in smoke_ids]
if len(smoke)!=3:p.error('O dataset não contém as três espécies do teste inicial')
report=run_batch(smoke,backend,a.out)
if report['failed']:print(json.dumps(report,indent=2));sys.exit(1)
report=run_batch(items,backend,a.out)
SpeciesIndex().build(items)
export_extension(items,a.out)
print(json.dumps(report,indent=2));sys.exit(1 if report['failed'] else 0)
