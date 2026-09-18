import multiprocessing
import os

# Força o macOS a usar o método seguro de multiprocessamento
multiprocessing.set_start_method('spawn', force=True)
os.environ["TOKENIZERS_PARALLELISM"] = "false"



import json
import os
import torch
from diffusers import StableDiffusionXLPipeline
from tqdm import tqdm

# ==========================================
# CONFIGURAÇÕES DE TESTE
# ==========================================
INPUT_JSON = '/Users/fernandodavilalbcfilho/Downloads/aquario/prompts_pixel_art.json'
OUTPUT_DIR = '/Users/fernandodavilalbcfilho/Downloads/aquario/sprites_teste'
LORA_PATH = '/Users/fernandodavilalbcfilho/Downloads/aquario/lora_pixel_art.safetensors'
MODEL_ID = "stabilityai/stable-diffusion-xl-base-1.0"

NUM_INFERENCE_STEPS = 25
GUIDANCE_SCALE = 7.0
WIDTH, HEIGHT = 1024, 1024
MAX_IMAGES = 5  # 👈 Gera apenas 5 para teste rápido

def main():
    print(f"🧪 MODO TESTE: Gerando {MAX_IMAGES} sprites (Rembg desativado para evitar crash no macOS)...")
    
    # Carrega modelo no MPS (Apple Silicon)
    print("🚀 Carregando SDXL para Apple Silicon (MPS)...")
    pipe = StableDiffusionXLPipeline.from_pretrained(
    MODEL_ID,
    dtype=torch.float16,
    use_safetensors=True,
    variant="fp16"
)
    pipe.to("mps")
    
    if os.path.exists(LORA_PATH):
        print(f"🎨 Carregando LoRA de Pixel Art: {LORA_PATH}")
        pipe.load_lora_weights(LORA_PATH)
        pipe.fuse_lora(lora_scale=0.8)
    else:
        print("⚠️  LoRA não encontrado em: " + LORA_PATH)
        print("   O script vai rodar, mas o estilo pode não ficar 100% pixel art sem ele.")
    
    # Lê JSON
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    prompts_list = data.get('dados', data)
    teste_list = prompts_list[:MAX_IMAGES]
    
    print(f"\n🐟 Espécies selecionadas:")
    for i, item in enumerate(teste_list, 1):
        print(f"   {i}. [{item['categoria'].upper()}] {item['nome_popular']}")
    
    print(f"\n⏱️  Tempo estimado: ~{MAX_IMAGES * 4} segundos\n")
    
    for item in tqdm(teste_list, desc="Gerando"):
        nome = item['nome_popular'].replace(' ', '_').replace('/', '_').replace('(', '').replace(')', '')
        categoria = item['categoria']
        prompt = item['prompt_pixel_art']
        
        cat_dir = os.path.join(OUTPUT_DIR, categoria)
        os.makedirs(cat_dir, exist_ok=True)
        
        output_path = os.path.join(cat_dir, f"{nome}.png")
        
        if os.path.exists(output_path):
            continue
        
        # Gera a imagem
        image = pipe(
            prompt=prompt,
            negative_prompt="photorealistic, 3d, smooth gradients, blurry, low resolution, text, watermark, signature, photograph",
            num_inference_steps=NUM_INFERENCE_STEPS,
            guidance_scale=GUIDANCE_SCALE,
            width=WIDTH,
            height=HEIGHT
        ).images[0]
        
        # Salva direto (sem rembg, evitando o crash de mutex)
        image.save(output_path, "PNG")

    print(f"\n{'='*60}")
    print(f"✅ TESTE CONCLUÍDO COM SUCESSO!")
    print(f"📁 Resultados salvos em: {OUTPUT_DIR}")
    print(f"👀 Para abrir a pasta no Finder, cole este comando no terminal:")
    print(f"   open {OUTPUT_DIR}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()