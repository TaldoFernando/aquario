from __future__ import annotations
import hashlib
import io
import json
import sqlite3
import time
import urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageColor, ImageFilter, ImageOps
from .catalog import ROOT

PIPELINE_VERSION = '2'

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False))
    tmp.replace(path)


def fetch_source(item, directory):
    path = Path(directory) / (item['id'] + '.png')
    meta = path.with_suffix('.json')
    if path.exists() and (not meta.exists() or json.loads(meta.read_text()).get('url') == item['image_url']):
        # Bundled smoke fixtures are deliberately usable without network.
        Image.open(path).verify()
        return path
    if not str(item['image_url']).startswith('https://'):
        raise ValueError('Imagem deve usar HTTPS')
    path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        try:
            request = urllib.request.Request(item['image_url'], headers={'User-Agent': 'AquarioSpritePipeline/0.1'})
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read(20_000_001)
            if len(raw) > 20_000_000:
                raise ValueError('Imagem excede 20 MB')
            image = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert('RGB')
            image.save(path)
            atomic_json(meta, {'url': item['image_url'], 'sha256': digest(path)})
            return path
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def transparent(image):
    image = image.convert('RGBA')
    a = np.asarray(image).copy()
    if (a[:, :, 3] < 128).any():
        return image
    # Opaque teacher outputs: remove only neutral background components touching
    # the border (including baked checkerboards), never isolated body highlights.
    rgb = a[:, :, :3].astype(int)
    neutral = (rgb.max(2) - rgb.min(2) < 18) & (rgb.min(2) > 105)
    h, w = neutral.shape
    visited = np.zeros((h, w), dtype=bool)
    stack = [(y, x) for y in (0, h-1) for x in range(w)] + [(y, x) for x in (0, w-1) for y in range(h)]
    while stack:
        y, x = stack.pop()
        if y < 0 or x < 0 or y >= h or x >= w or visited[y, x] or not neutral[y, x]:
            continue
        visited[y, x] = True
        stack.extend(((y-1, x), (y+1, x), (y, x-1), (y, x+1)))
    if visited.mean() < .03:
        raise ValueError('Sem alpha ou fundo neutro removível; regenerar com fundo branco/transparente')
    a[visited, 3] = 0
    # Remove enclosed checkerboard holes only if both known border shades occur.
    # Conservative: rembg backend is available for complicated opaque backgrounds.
    border_colors = rgb[visited]
    if len(border_colors) and np.std(border_colors[:, 0]) > 12:
        a[neutral, 3] = 0
    return Image.fromarray(a)


def normalize(image, style):
    image = transparent(image)
    alpha = image.getchannel('A').point(lambda a: 255 if a >= 128 else 0)
    bbox = alpha.getbbox()
    if bbox is None:
        raise ValueError('Sprite vazio')
    image.putalpha(alpha)
    image = image.crop(bbox)
    grid, pad = style['grid'], style['padding']
    image.thumbnail((grid-2*pad, grid-2*pad), Image.Resampling.NEAREST)
    canvas = Image.new('RGBA', (grid, grid))
    canvas.paste(image, ((grid-image.width)//2, (grid-image.height)//2))
    a = np.asarray(canvas).copy()
    palette = np.array([ImageColor.getrgb(c) for c in style['palette']], dtype=np.int32)
    flat = a[:, :, :3].astype(np.int32)
    distances = ((flat[:, :, None, :] - palette[None, None, :, :]) ** 2).sum(3)
    a[:, :, :3] = palette[distances.argmin(2)]
    a[:, :, 3] = (a[:, :, 3] >= 128) * 255
    # Deterministic one-grid-pixel exterior contour. Interior drawing is preserved.
    mask = Image.fromarray(a[:, :, 3])
    expanded = np.asarray(mask.filter(ImageFilter.MaxFilter(3)))
    outline = (expanded > 0) & (a[:, :, 3] == 0)
    a[outline, :3] = ImageColor.getrgb(style['outline'])
    a[outline, 3] = 255
    a[a[:, :, 3] == 0, :3] = 0
    result = Image.fromarray(a)
    check_sprite(result, style)
    return result


def check_sprite(image, style):
    a = np.asarray(image.convert('RGBA'))
    mask = a[:, :, 3] > 0
    colors = {tuple(c) for c in a[:, :, :3][mask]}
    allowed = {ImageColor.getrgb(c) for c in style['palette']}
    if image.size != (style['grid'], style['grid']) or not colors.issubset(allowed):
        raise ValueError('Grid ou paleta inválidos')
    if not set(np.unique(a[:, :, 3])).issubset({0, 255}) or not .02 < mask.mean() < .8:
        raise ValueError('Alpha ou ocupação inválidos')
    if mask[0].any() or mask[-1].any() or mask[:, 0].any() or mask[:, -1].any():
        raise ValueError('Sprite toca a borda')
    return {'colors': len(colors), 'occupancy': round(float(mask.mean()), 4), 'grid': style['grid'], 'alpha': 'binary'}


class ReferenceBackend:
    name = 'teacher-reference'
    def __init__(self, directory):
        self.directory = Path(directory)
    def fingerprint(self, item):
        return digest(self.directory / (item['id'] + '.png'))
    def generate(self, source, item, prompt, seed):
        return Image.open(self.directory / (item['id'] + '.png')).copy()


class QwenBackend:
    name = 'qwen-edit-2509'
    def __init__(self, lora=None, anchors=(), revision=None):
        self.lora, self.anchors, self.revision = lora, list(map(Path, anchors)), revision
        self.pipe = None
    def fingerprint(self, item):
        if self.lora and not Path(self.lora).is_file():
            raise ValueError('--lora deve apontar para um arquivo safetensors local')
        return json.dumps({'model': self.name, 'revision': self.revision, 'lora': digest(self.lora) if self.lora else None, 'anchors': [digest(p) for p in self.anchors]})
    def generate(self, source, item, prompt, seed):
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError('Qwen requer worker CUDA; não foi iniciada geração simulada.')
        if self.pipe is None:
            from diffusers import QwenImageEditPlusPipeline
            self.pipe = QwenImageEditPlusPipeline.from_pretrained('Qwen/Qwen-Image-Edit-2509', torch_dtype=torch.bfloat16, revision=self.revision)
            self.pipe.enable_model_cpu_offload()
            if self.lora:
                self.pipe.load_lora_weights(str(Path(self.lora).parent), weight_name=Path(self.lora).name)
        images = [Image.open(source).convert('RGB')]
        for p in self.anchors[:2]:
            anchor = Image.open(p).convert('RGBA')
            bg = Image.new('RGBA', anchor.size, 'white'); bg.alpha_composite(anchor)
            images.append(bg.convert('RGB'))
        with torch.inference_mode():
            return self.pipe(image=images, prompt=prompt, negative_prompt=' ', num_inference_steps=40, true_cfg_scale=4.0, generator=torch.Generator(device='cpu').manual_seed(seed)).images[0]


class DiffSynthBackend(QwenBackend):
    """Native inference for LoRAs produced by scripts/train_lora.py.

    DiffSynth and Diffusers adapter key layouts are not assumed interchangeable.
    """
    name = 'diffsynth-qwen-edit-2509'
    def generate(self, source, item, prompt, seed):
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError('DiffSynth requer GPU CUDA')
        if self.pipe is None:
            from diffsynth.pipelines.qwen_image import QwenImagePipeline, ModelConfig
            self.pipe = QwenImagePipeline.from_pretrained(
                torch_dtype=torch.bfloat16, device='cuda', model_configs=[
                    ModelConfig(model_id='Qwen/Qwen-Image-Edit-2509', origin_file_pattern='transformer/diffusion_pytorch_model*.safetensors'),
                    ModelConfig(model_id='Qwen/Qwen-Image', origin_file_pattern='text_encoder/model*.safetensors'),
                    ModelConfig(model_id='Qwen/Qwen-Image', origin_file_pattern='vae/diffusion_pytorch_model.safetensors'),
                ], tokenizer_config=None,
                processor_config=ModelConfig(model_id='Qwen/Qwen-Image-Edit', origin_file_pattern='processor/'))
            if self.lora:
                self.pipe.load_lora(self.pipe.dit, self.lora)
        images = [ImageOps.pad(Image.open(source).convert('RGB'), (768,768), color='white')]
        for path in self.anchors[:2]:
            im = Image.open(path).convert('RGBA')
            bg = Image.new('RGBA', im.size, 'white'); bg.alpha_composite(im)
            images.append(bg.convert('RGB'))
        return self.pipe(prompt, edit_image=images, seed=seed, num_inference_steps=40, height=768, width=768)


def run_batch(items, backend, out=ROOT/'data/generated', style_path=ROOT/'config/style.json'):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    style = json.loads(Path(style_path).read_text())
    db = sqlite3.connect(out / 'jobs.sqlite')
    db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, fingerprint TEXT, status TEXT, error TEXT, attempts INTEGER DEFAULT 0)')
    report = {'success': [], 'cached': [], 'failed': [], 'skipped': []}
    for item in items:
        sid = item['id']
        if not item['eligible']:
            report['skipped'].append(sid); continue
        try:
            source = fetch_source(item, ROOT/'data/sources')
            prompt = style['prompt'] + f' Subject: {item["name"]}; {item["scientific_name"] or ""}; category: {item["kind"]}.'
            seed = int(sid[:8], 16)
            fingerprint = hashlib.sha256((digest(source)+json.dumps(style, sort_keys=True)+backend.fingerprint(item)+prompt+PIPELINE_VERSION).encode()).hexdigest()
            target = out / (sid + '.png')
            row = db.execute('SELECT fingerprint,status FROM jobs WHERE id=?', (sid,)).fetchone()
            if row == (fingerprint, 'done') and target.exists() and target.with_suffix('.json').exists():
                check_sprite(Image.open(target), style)
                report['cached'].append(sid); continue
            db.execute('INSERT INTO jobs(id,fingerprint,status,attempts) VALUES(?,?,?,1) ON CONFLICT(id) DO UPDATE SET fingerprint=excluded.fingerprint,status=excluded.status,error=NULL,attempts=jobs.attempts+1', (sid, fingerprint, 'running')); db.commit()
            image = backend.generate(source, item, prompt, seed)
            raw_path = out / (sid + '.raw.png'); image.save(raw_path)
            sprite = normalize(image, style)
            temp = target.with_suffix('.tmp.png'); sprite.save(temp); temp.replace(target)
            metadata = {'id': sid, 'name': item['name'], 'source_url': item['image_url'], 'source_sha256': digest(source), 'backend': backend.name, 'backend_fingerprint': backend.fingerprint(item), 'style': style['version'], 'prompt': prompt, 'seed': seed, 'fingerprint': fingerprint, 'qa': check_sprite(sprite, style), 'semantic_review': 'required'}
            atomic_json(target.with_suffix('.json'), metadata)
            db.execute('UPDATE jobs SET status=?,error=NULL WHERE id=?', ('done', sid)); db.commit()
            report['success'].append(sid)
        except Exception as exc:
            db.execute('INSERT INTO jobs(id,status,error) VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET status=excluded.status,error=excluded.error', (sid, 'failed', str(exc))); db.commit()
            report['failed'].append({'id': sid, 'error': str(exc)})
    db.close(); atomic_json(out/'report.json', report)
    return report
