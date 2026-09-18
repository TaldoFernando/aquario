"""Runnable photo -> pixel-art preset using exactly Qwen/Qwen-Image.

No image weights are bundled or claimed to have been fine-tuned.
Heavy imports/model downloads happen only after validation, never in --dry-run.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass, asdict
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import sys
import time
from PIL import Image, ImageOps
from .catalog import ROOT, load_catalog
from .sprites import atomic_json, check_sprite, digest, fetch_source, normalize

MODEL = 'Qwen/Qwen-Image'
VERSION = 'qwen-pixelart-1'
EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}

@dataclass(frozen=True)
class Settings:
    revision: str = 'main'
    resolution: int = 768
    strength: float = .65
    steps: int = 40
    cfg: float = 4.0
    seed: int = 42
    offload: str = 'model'
    remove_background: bool = False
    lora: str | None = None
    device: str = 'auto'

    def validate(self):
        if not 0 < self.strength <= 1 or not math.isfinite(self.strength):
            raise ValueError('strength deve estar entre 0 (exclusivo) e 1')
        if self.steps < 1 or int(self.steps*self.strength) < 1:
            raise ValueError('steps × strength deve permitir pelo menos um passo de difusão')
        if self.resolution < 256 or self.resolution > 1536 or self.resolution % 16:
            raise ValueError('resolution deve ser múltiplo de 16 entre 256 e 1536')
        if not math.isfinite(self.cfg) or self.cfg <= 1:
            raise ValueError('cfg deve ser maior que 1 para ativar o prompt negativo')
        if not 0 <= self.seed < 2**32:
            raise ValueError('seed deve ser um inteiro de 0 a 2³²−1')
        if self.offload not in ('model', 'sequential', 'none'):
            raise ValueError('offload inválido')
        if self.device not in ('auto', 'cuda', 'mps', 'cpu'):
            raise ValueError('device deve ser auto, cuda, mps ou cpu')
        if self.lora and not Path(self.lora).is_file():
            raise ValueError('Arquivo LoRA não encontrado')
        return self


class Foreground:
    def __init__(self):
        self.session = None
    def remove(self, image):
        from rembg import new_session, remove
        if self.session is None:
            self.session = new_session('isnet-general-use', providers=['CPUExecutionProvider'])
        return remove(image, session=self.session).convert('RGBA')


def prepare(image, resolution, foreground=None):
    image = ImageOps.exif_transpose(image).convert('RGBA')
    if foreground:
        image = foreground.remove(image)
    bbox = image.getchannel('A').getbbox()
    if not bbox:
        raise ValueError('Segmentação removeu o organismo inteiro; tente sem --remove-background')
    image = image.crop(bbox)
    image.thumbnail((int(resolution*.84), int(resolution*.84)), Image.Resampling.LANCZOS)
    canvas = Image.new('RGBA', (resolution, resolution), 'white')
    canvas.alpha_composite(image, ((resolution-image.width)//2, (resolution-image.height)//2))
    return canvas.convert('RGB')


class QwenPhotoModel:
    """Img2img initializes diffusion with photo latents; not text-only generation."""
    def __init__(self, settings):
        self.settings = settings.validate()
        self.pipe = None
        self.runtime = {}
        self.device = None

    def load(self):
        if self.pipe is not None:
            return
        os.environ.setdefault('USE_TF', '0')
        os.environ.setdefault('USE_FLAX', '0')
        os.environ.setdefault('HF_HOME', str(ROOT/'data/cache/huggingface'))
        import torch
        s = self.settings
        cuda = torch.cuda.is_available()
        mps = torch.backends.mps.is_available()
        if s.device == 'auto':
            self.device = 'cuda' if cuda else 'mps' if mps else 'cpu'
        else:
            self.device = s.device
        if self.device == 'cuda' and not cuda:
            raise RuntimeError('CUDA não está disponível; use --device mps neste Mac ou --device auto')
        if self.device == 'mps' and not mps:
            raise RuntimeError('MPS não está disponível neste ambiente; use --device cpu ou --device auto')
        from diffusers import QwenImageImg2ImgPipeline
        dtype = torch.bfloat16 if self.device == 'cuda' and torch.cuda.is_bf16_supported() else torch.float16 if self.device == 'mps' else torch.float32
        self.pipe = QwenImageImg2ImgPipeline.from_pretrained(MODEL, revision=s.revision, torch_dtype=dtype, use_safetensors=True)
        if s.lora:
            self.pipe.load_lora_weights(str(Path(s.lora).resolve().parent), weight_name=Path(s.lora).name)
        self.pipe.vae.enable_tiling()
        if s.offload == 'model' and self.device in ('cuda', 'mps'):
            self.pipe.enable_model_cpu_offload(device=self.device)
        elif s.offload == 'sequential' and self.device in ('cuda', 'mps'):
            self.pipe.enable_sequential_cpu_offload(device=self.device)
        else:
            self.pipe.to(self.device)
        self.runtime = {'torch': torch.__version__, 'diffusers': importlib.metadata.version('diffusers'), 'transformers': importlib.metadata.version('transformers'), 'device': self.device, 'gpu': torch.cuda.get_device_name(0) if self.device == 'cuda' else None, 'dtype': str(dtype), 'requested_revision': s.revision}

    def generate(self, image, prompt, negative_prompt, seed):
        self.load()
        import torch
        s = self.settings
        with torch.inference_mode():
            return self.pipe(image=image, prompt=prompt, negative_prompt=negative_prompt,
                             strength=s.strength, num_inference_steps=s.steps,
                             true_cfg_scale=s.cfg, width=s.resolution, height=s.resolution,
                             generator=torch.Generator(device='cpu').manual_seed(seed)).images[0]


def select_jobs(input_path=None, dataset=None, smoke=False, limit=3, all_items=False, subject=None):
    if input_path:
        path = Path(input_path).resolve()
        files = sorted(p for p in path.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONS) if path.is_dir() else [path]
        if not files or any(not p.is_file() or p.suffix.lower() not in EXTENSIONS for p in files):
            raise ValueError('Nenhuma foto PNG/JPG/WEBP/BMP válida encontrada')
        return [{'id': p.stem[:60]+'-'+hashlib.sha256(str(p).encode()).hexdigest()[:8], 'subject': subject or 'aquatic organism', 'path': p} for p in files]
    items = [i for i in load_catalog(dataset) if i['eligible']]
    if smoke:
        ids = {i['id'] for i in json.loads((ROOT/'config/smoke.json').read_text())}
        items = [i for i in items if i['id'] in ids]
        if len(items) != 3:
            raise ValueError('As três espécies do smoke não estão no dataset')
    elif not all_items:
        if limit < 1: raise ValueError('limit deve ser positivo')
        items = items[:limit]
    return [{'id': i['id'], 'subject': subject or f'{i["name"]} ({i["scientific_name"] or i["kind"]})', 'item': i} for i in items]


def convert_jobs(jobs, settings, output, preset, style, model=None, resume=True):
    settings.validate()
    model = model or QwenPhotoModel(settings)
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    foreground = Foreground() if settings.remove_background else None
    report = {'model': MODEL, 'version': VERSION, 'success': [], 'cached': [], 'failed': []}
    # Fail before fetching 600 photos when the worker cannot run the model.
    model.load()
    for n, job in enumerate(jobs, 1):
        sid = job['id']; start = time.monotonic(); prefix = output/sid
        print(f'[{n}/{len(jobs)}] {job["subject"]}', flush=True)
        try:
            source = job.get('path') or fetch_source(job['item'], ROOT/'data/sources')
            image = Image.open(source); image.load()
            seed = (settings.seed + int(hashlib.sha256(sid.encode()).hexdigest()[:8],16)) % 2**32
            prompt = preset['prompt'].replace('{subject}', job['subject'])
            key = {'version': VERSION, 'model': MODEL, 'settings': asdict(settings), 'source_sha256': digest(source), 'style': style, 'prompt': prompt, 'negative_prompt': preset['negative_prompt'], 'lora_sha256': digest(settings.lora) if settings.lora else None}
            fingerprint = hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()
            paths = {kind: Path(str(prefix)+suffix) for kind,suffix in [('sprite','.png'),('raw','.raw.png'),('prepared','.input.png'),('preview','.preview.png'),('metadata','.json')]}
            if resume and all(p.exists() for p in paths.values()):
                previous = json.loads(paths['metadata'].read_text())
                if previous.get('fingerprint') == fingerprint and previous.get('status') == 'done':
                    try:
                        check_sprite(Image.open(paths['sprite']),style)
                        report['cached'].append(sid); continue
                    except (OSError, ValueError):
                        pass  # Corrupt cached sprite must be regenerated.
            metadata = {**key, 'id': sid, 'fingerprint': fingerprint, 'seed': seed, 'source': str(source), 'status': 'running', 'runtime': model.runtime}
            atomic_json(paths['metadata'],metadata)
            prepared = prepare(image, settings.resolution, foreground); prepared.save(paths['prepared'])
            raw = model.generate(prepared,prompt,preset['negative_prompt'],seed); raw.save(paths['raw'])
            segmented = foreground.remove(raw) if foreground else raw
            sprite = normalize(segmented,style)
            sprite.save(paths['sprite'])
            sprite.resize((style['grid']*4,style['grid']*4),Image.Resampling.NEAREST).save(paths['preview'])
            metadata.update(status='done',seconds=round(time.monotonic()-start,2),qa=check_sprite(sprite,style),visual_review='required')
            atomic_json(paths['metadata'],metadata); report['success'].append(sid)
        except Exception as exc:
            failure={'id':sid,'error':str(exc),'status':'failed','seconds':round(time.monotonic()-start,2)}
            atomic_json(Path(str(prefix)+'.error.json'),failure)
            # Do not leave an old success marker after a failed regeneration.
            if Path(str(prefix)+'.json').exists():
                previous=json.loads(Path(str(prefix)+'.json').read_text());previous.update(status='failed',error=str(exc));atomic_json(Path(str(prefix)+'.json'),previous)
            report['failed'].append(failure)
            print(f'  Falhou: {exc}',file=sys.stderr,flush=True)
        finally:
            atomic_json(output/'report.json', report)
    atomic_json(output/'report.json', report)
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description='Foto → pixel art com Qwen/Qwen-Image (img2img)')
    source=p.add_mutually_exclusive_group(required=True)
    source.add_argument('--input',type=Path,help='Foto ou pasta de fotos')
    source.add_argument('--dataset',type=Path,help='JSON do catálogo Kauar')
    p.add_argument('--subject',help='Descrição da espécie e suas marcas; recomendável para foto avulsa')
    selection=p.add_mutually_exclusive_group();selection.add_argument('--smoke',action='store_true');selection.add_argument('--all',action='store_true');selection.add_argument('--limit',type=int,default=3)
    p.add_argument('--preset',type=Path,default=ROOT/'config/qwen_pixelart.json')
    p.add_argument('--style',type=Path,default=ROOT/'config/style.json')
    p.add_argument('--output',type=Path,default=ROOT/'output/qwen-pixelart')
    for name,kind in [('strength',float),('steps',int),('cfg',float),('seed',int),('resolution',int)]:p.add_argument('--'+name,type=kind)
    p.add_argument('--offload',choices=['model','sequential','none'])
    p.add_argument('--device',choices=['auto','cuda','mps','cpu'])
    p.add_argument('--revision');p.add_argument('--lora');p.add_argument('--remove-background',action='store_true')
    p.add_argument('--dry-run',action='store_true');p.add_argument('--force',action='store_true')
    args=p.parse_args(argv)
    try:
        preset=json.loads(args.preset.read_text());style=json.loads(args.style.read_text())
        if preset['model_id']!=MODEL or preset['pipeline']!='QwenImageImg2ImgPipeline':
            raise ValueError('Este pacote usa exatamente Qwen/Qwen-Image e QwenImageImg2ImgPipeline')
        if args.input and (args.smoke or args.all):raise ValueError('--smoke/--all são exclusivos de --dataset')
        settings=Settings(**{k:getattr(args,k) if getattr(args,k) is not None else preset[k] for k in ('revision','resolution','strength','steps','cfg','seed','offload')},device=args.device or preset.get('device','auto'),remove_background=args.remove_background,lora=args.lora).validate()
        jobs=select_jobs(args.input,args.dataset,args.smoke,args.limit,args.all,args.subject)
        if args.dry_run:
            print(json.dumps({'model':MODEL,'pipeline':preset['pipeline'],'settings':asdict(settings),'count':len(jobs),'jobs':[{'id':j['id'],'subject':j['subject'],'source':str(j.get('path') or j['item']['image_url'])} for j in jobs],'downloads':False,'inference_executed':False},indent=2,ensure_ascii=False));return 0
        report=convert_jobs(jobs,settings,args.output,preset,style,resume=not args.force)
        print(json.dumps(report,indent=2,ensure_ascii=False));return 1 if report['failed'] else 0
    except (ValueError, OSError, RuntimeError, ImportError, KeyError) as exc:
        print(f'Erro: {exc}',file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
