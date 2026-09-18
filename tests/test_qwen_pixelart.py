import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from PIL import Image, ImageDraw
from aquarium.catalog import ROOT
from aquarium.qwen_pixelart import Settings, QwenPhotoModel, prepare, select_jobs, convert_jobs, main

@pytest.mark.parametrize('kwargs',[{'strength':0},{'strength':1.1},{'strength':float('nan')},{'steps':1,'strength':.1},{'resolution':767},{'cfg':float('nan')},{'seed':-1}])
def test_invalid_configuration(kwargs):
    with pytest.raises(ValueError):Settings(**kwargs).validate()

def test_prepare_preserves_aspect_and_alpha():
    im=Image.new('RGBA',(200,100),(255,0,0,255));out=prepare(im,768)
    assert out.size==(768,768) and out.mode=='RGB'
    assert out.getpixel((0,0))==(255,255,255)
    assert out.getpixel((384,384))==(255,0,0)
    with pytest.raises(ValueError):prepare(Image.new('RGBA',(100,100)),768)

def test_actual_photo_is_passed_to_img2img():
    calls=[]
    class Pipeline:
        def __call__(self,**kwargs):calls.append(kwargs);return SimpleNamespace(images=[kwargs['image']])
    model=QwenPhotoModel(Settings(strength=.55));model.pipe=Pipeline()
    photo=Image.new('RGB',(768,768),'blue')
    result=model.generate(photo,'sprite','photo',13)
    assert result is photo
    assert calls[0]['image'] is photo and calls[0]['strength']==.55
    assert calls[0]['generator'].initial_seed()==13
    assert calls[0]['true_cfg_scale']==4

class FakeModel:
    """Unit-test double; never used by the CLI or delivered as model output."""
    runtime={'test_double':True}
    def __init__(self):self.calls=0
    def load(self):pass
    def generate(self,image,prompt,negative_prompt,seed):
        self.calls+=1
        out=Image.new('RGBA',(256,256));ImageDraw.Draw(out).ellipse((40,90,216,160),fill='#e5b54a');return out

def test_conversion_cache_content_invalidation_and_corruption(tmp_path):
    source=tmp_path/'photo.png';Image.new('RGB',(100,70),'red').save(source)
    jobs=select_jobs(input_path=source,subject='goby');model=FakeModel()
    preset=json.loads((ROOT/'config/qwen_pixelart.json').read_text());style=json.loads((ROOT/'config/style.json').read_text())
    out=tmp_path/'out';s=Settings()
    first=convert_jobs(jobs,s,out,preset,style,model)
    assert len(first['success'])==1
    assert len(convert_jobs(jobs,s,out,preset,style,model)['cached'])==1 and model.calls==1
    Image.new('RGB',(100,70),'green').save(source)
    assert len(convert_jobs(jobs,s,out,preset,style,model)['success'])==1 and model.calls==2
    (out/(jobs[0]['id']+'.png')).write_bytes(b'broken')
    assert len(convert_jobs(jobs,s,out,preset,style,model)['success'])==1 and model.calls==3
    metadata=json.loads((out/(jobs[0]['id']+'.json')).read_text())
    assert metadata['model']=='Qwen/Qwen-Image' and metadata['status']=='done'

def test_dry_run_selects_three_and_no_load(monkeypatch,capsys):
    monkeypatch.setattr(QwenPhotoModel,'load',lambda _:pytest.fail('Must not load weights'))
    assert main(['--dataset',str(ROOT/'kauar_peixes.json'),'--smoke','--dry-run'])==0
    result=json.loads(capsys.readouterr().out)
    assert result['count']==3 and result['inference_executed'] is False

def test_normalization_failure_preserves_raw(tmp_path):
    class OpaqueModel(FakeModel):
        def generate(self,*args):return Image.new('RGB',(256,256),'green')
    photo=tmp_path/'fish.png';Image.new('RGB',(100,100),'blue').save(photo)
    jobs=select_jobs(input_path=photo);out=tmp_path/'out'
    r=convert_jobs(jobs,Settings(),out,json.loads((ROOT/'config/qwen_pixelart.json').read_text()),json.loads((ROOT/'config/style.json').read_text()),OpaqueModel())
    assert len(r['failed'])==1 and not r['success']
    assert (out/(jobs[0]['id']+'.raw.png')).exists()
    assert json.loads((out/(jobs[0]['id']+'.json')).read_text())['status']=='failed'
