import json
import os
import requests
import torch
import pandas as pd
from PIL import Image
from io import BytesIO
from diffusers import StableDiffusionXLImg2ImgPipeline  # ✅ CORREÇÃO: Pipeline específica para SDXL
from tqdm import tqdm

# ==========================================
# CONFIGURAÇÕES
# ==========================================
INPUT_JSON = '/Users/fernandodavilalbcfilho/Downloads/aquario/prompts_pixel_art.json'
OUTPUT_DIR = '/Users/fernandodavilalbcfilho/Downloads/aquario/sprites_img2img'
LORA_PATH = '/Users/fernandodavilalbcfilho/Downloads/aquario/lora_pixel_art.safetensors'
MODEL_ID = "stabilityai/stable-diffusion-xl-base-1.0"

NUM_INFERENCE_STEPS = 25
GUIDANCE_SCALE = 7.5
STRENGTH = 0.65  # Equilíbrio ideal: respeita a foto, mas aplica o estilo
WIDTH, HEIGHT = 1024, 1024
MAX_IMAGES = 5

def baixar_imagem(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content)).convert("RGB")
        return img
    except Exception as e:
        print(f"  ⚠️  Erro ao baixar {url}: {e}")
        return None

def gerar_prompt_curto(row, categoria):
    nome = str(row.get('nome_popular', 'Fish'))
    cientifico = str(row.get('nome_cientifico', '')) if pd.notna(row.get('nome_cientifico')) else ""
    desc = str(row.get('raw_description_snippet', '')).lower() if pd.notna(row.get('raw_description_snippet')) else ""
    
    traits = []
    if any(x in desc for x in ['amarelo', 'listra', 'preta', 'abelha', 'bumblebee']): traits.append("yellow body with black vertical stripes")
    if any(x in desc for x in ['vermelho', 'red', 'sakura', 'cherry']): traits.append("bright red segmented body")
    if any(x in desc for x in ['prateado', 'prata', 'silver']): traits.append("silvery metallic body")
    if any(x in desc for x in ['azul', 'blue']): traits.append("blue iridescent scales")
    if any(x in desc for x in ['agulha', 'bico', 'pontiagudo', 'dermogenys']): traits.append("elongated lower jaw")
    if any(x in desc for x in ['tubarão', 'shark', 'balashark']): traits.append("triangular dorsal fin, shark-like body shape")
    
    trait_str = ", ".join(traits) if traits else "distinctive ornamental colors"
    
    base = f"16-bit pixel art sprite of a {nome} ({cientifico}), {trait_str}, side view facing right, transparent background, chunky square pixels, dark navy outline, flat colors, game asset, high quality, no text, no watermark"
    
    if categoria == 'camarao':
        return base.replace("side view facing right", "side view facing right, segmented shell, tiny legs and two long antennae")
    elif categoria == 'planta':
        return f"16-bit pixel art sprite of a {nome} ({cientifico}), natural leaf shapes, stems and root structure, centered, transparent background, chunky square pixels, dark navy outline, flat colors, game asset, high quality, no text, no watermark"
    elif categoria == 'ampularia':
        return base.replace("side view facing right", "side view, spiral shell, soft body and antennae")
    
    return base

def main():
    print(f"🧪 MODO TESTE: Gerando {MAX_IMAGES} sprites com img2img (Prompts Otimizados)...")
    
    print("🚀 Carregando SDXL para Apple Silicon (MPS)...")
    # ✅ CORREÇÃO PRINCIPAL: Usar a pipeline específica para SDXL
    pipe = StableDiffusionXLImg2ImgPipeline.from_pretrained(
        MODEL_ID, 
        torch_dtype=torch.float16, 
        use_safetensors=True, 
        variant="fp16"
    )
    pipe.to("mps")
    pipe.enable_attention_slicing() # Otimiza o uso de memória no Mac
    
    if os.path.exists(LORA_PATH):
        print(f"🎨 Carregando LoRA de Pixel Art: {LORA_PATH}")
        pipe.load_lora_weights(LORA_PATH)
        pipe.fuse_lora(lora_scale=0.8)
    else:
        print("⚠️  LoRA não encontrado. Gerando sem LoRA.")
        print("💡 Dica: Baixe um LoRA 'Pixel Art SDXL' no CivitAI para resultados perfeitos.")
    
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    prompts_list = data.get('dados', data)
    teste_list = prompts_list[:MAX_IMAGES]
    
    print(f"\n🐟 Espécies selecionadas:")
    for i, item in enumerate(teste_list, 1):
        print(f"   {i}. [{item['categoria'].upper()}] {item['nome_popular']}")
    
    print(f"\n⏱️  Tempo estimado: ~{MAX_IMAGES * 5} segundos\n")
    
    for item in tqdm(teste_list, desc="Gerando"):
        nome = item['nome_popular'].replace(' ', '_').replace('/', '_').replace('(', '').replace(')', '')
        categoria = item['categoria']
        url_imagem = item.get('url_imagem', '')
        
        if not url_imagem:
            print(f"\n⚠️  Sem URL para {nome}, pulando...")
            continue
        
        cat_dir = os.path.join(OUTPUT_DIR, categoria)
        os.makedirs(cat_dir, exist_ok=True)
        output_path = os.path.join(cat_dir, f"{nome}.png")
        
        if os.path.exists(output_path):
            print(f"\n⏭️  Pulando {nome} (já existe)")
            continue
        
        print(f"\n📥 Baixando referência: {nome}")
        init_image = baixar_imagem(url_imagem)
        if init_image is None:
            continue
        
        init_image = init_image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
        prompt = gerar_prompt_curto(item, categoria)
        
        try:
            image = pipe(
                prompt=prompt,
                image=init_image,
                negative_prompt="photorealistic, 3d, smooth gradients, blurry, photograph, realistic, text, watermark, signature",
                num_inference_steps=NUM_INFERENCE_STEPS,
                guidance_scale=GUIDANCE_SCALE,
                strength=STRENGTH,
                width=WIDTH,
                height=HEIGHT
            ).images[0]
            
            image.save(output_path, "PNG")
            print(f"✅ Salvo com sucesso: {output_path}")
            
        except Exception as e:
            print(f"❌ Erro ao gerar {nome}: {e}")
            continue

    print(f"\n{'='*60}")
    print(f"✅ TESTE CONCLUÍDO!")
    print(f"📁 Resultados em: {OUTPUT_DIR}")
    print(f"👀 Para abrir a pasta no Finder, execute:")
    print(f"   open {OUTPUT_DIR}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()