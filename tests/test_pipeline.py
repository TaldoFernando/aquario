import json
from pathlib import Path
import pytest
from PIL import Image
from aquarium.catalog import ROOT, load_catalog
from aquarium.sprites import ReferenceBackend, run_batch, check_sprite, normalize
from scripts.prepare_pairs import prepare

@pytest.fixture
def trio():
    ids={r['id'] for r in json.loads((ROOT/'config/smoke.json').read_text())}
    return [i for i in load_catalog() if i['id'] in ids]

def test_three_real_sprites_cache_and_recovery(tmp_path,trio):
    backend=ReferenceBackend(ROOT/'data/references')
    first=run_batch(trio,backend,tmp_path)
    assert len(first['success'])==3 and not first['failed']
    assert len(run_batch(trio,backend,tmp_path)['cached'])==3
    (tmp_path/(trio[0]['id']+'.png')).unlink()
    recovered=run_batch(trio,backend,tmp_path)
    assert len(recovered['success'])==1 and len(recovered['cached'])==2
    style=json.loads((ROOT/'config/style.json').read_text())
    for i in trio:assert check_sprite(Image.open(tmp_path/(i['id']+'.png')),style)['alpha']=='binary'

def test_style_change_invalidates_cache(tmp_path,trio):
    style=json.loads((ROOT/'config/style.json').read_text());sp=tmp_path/'style.json';sp.write_text(json.dumps(style))
    backend=ReferenceBackend(ROOT/'data/references');run_batch(trio[:1],backend,tmp_path,sp)
    style['version']='new';sp.write_text(json.dumps(style))
    assert len(run_batch(trio[:1],backend,tmp_path,sp)['success'])==1

def test_missing_reference_reported_not_faked(tmp_path,trio):
    report=run_batch(trio,ReferenceBackend(tmp_path/'absent'),tmp_path)
    assert len(report['failed'])==3 and not report['success']

def test_empty_sprite_rejected():
    with pytest.raises(ValueError):normalize(Image.new('RGBA',(100,100)),json.loads((ROOT/'config/style.json').read_text()))

def test_pairs_group_split(tmp_path):
    result=prepare(ROOT/'kauar_peixes.json',ROOT/'data/generated',tmp_path)
    assert result['pairs']==3 and not result['training_ready']
    train=json.loads((tmp_path/'train.json').read_text());val=json.loads((tmp_path/'validation.json').read_text())
    assert {r['image'] for r in train}.isdisjoint({r['image'] for r in val})
    assert all((tmp_path/r['edit_image'][0]).exists() for r in train+val)
