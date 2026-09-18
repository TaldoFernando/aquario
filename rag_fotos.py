import os
import json
import pandas as pd
import requests
from PIL import Image
from io import BytesIO
from tqdm import tqdm
import re

# ==========================================
# CONFIGURAÇÕES
# ==========================================
# Use 'dados.json' ou 'dados.csv' aqui
INPUT_FILE = 'kauar_peixes.json' 
OUTPUT_DIR = 'dataset_aquario'
IMAGE_SIZE = (512, 512) # Tamanho padrão para treinamento (pode ser 1024x1024 para modelos novos)

# Headers para simular um navegador e evitar bloqueio 403 de CDNs de e-commerce
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================
def limpar_nome_arquivo(nome):
    """Remove caracteres inválidos para nomes de arquivo."""
    nome = re.sub(r'[^\w\s-]', '', nome).strip().lower()
    return re.sub(r'[-\s]+', '_', nome)

def limpar_descricao(descricao):
    """Limpa a descrição bruta para criar um prompt de treinamento eficaz."""
    if pd.isna(descricao) or not descricao:
        return "Uma foto de um peixe ornamental de aquário."
    
    # Remove quebras de linha excessivas e espaços
    texto_limpo = " ".join(descricao.split())
    return texto_limpo[:500] # Limita a 500 caracteres para evitar ruído

def baixar_e_processar_imagem(url, save_path):
    """Baixa a imagem, converte para RGB e redimensiona."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        img = Image.open(BytesIO(response.content))
        
        # Converte para RGB (remove transparência de PNGs que pode quebrar o treinamento)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        # Redimensiona mantendo a proporção e preenchendo com branco se necessário (pad)
        img.thumbnail(IMAGE_SIZE, Image.Resampling.LANCZOS)
        
        # Cria um fundo branco e cola a imagem no centro (opcional, mas bom para padronização)
        novo_img = Image.new("RGB", IMAGE_SIZE, (255, 255, 255))
        offset = ((IMAGE_SIZE[0] - img.width) // 2, (IMAGE_SIZE[1] - img.height) // 2)
        novo_img.paste(img, offset)
        
        novo_img.save(save_path, "JPEG", quality=95)
        return True
    except Exception as e:
        print(f"\n[ERRO] ao baixar {url}: {e}")
        return False

# ==========================================
# FLUXO PRINCIPAL
# ==========================================
def main():
    print(f"📂 Lendo arquivo: {INPUT_FILE}")
    
    # Lê CSV ou JSON automaticamente pela extensão
    if INPUT_FILE.endswith('.csv'):
        df = pd.read_csv(INPUT_FILE)
    else:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            df = pd.DataFrame(json.load(f))

    # Cria diretórios de saída
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    imagens_dir = os.path.join(OUTPUT_DIR, "imagens")
    os.makedirs(imagens_dir, exist_ok=True)

    metadados = []
    sucessos = 0
    falhas = 0

    print(f"🚀 Iniciando processamento de {len(df)} registros...")
    
    for index, row in tqdm(df.iterrows(), total=len(df)):
        nome_popular = str(row.get('nome_popular', 'desconhecido'))
        nome_cientifico = str(row.get('nome_cientifico', 'desconhecido'))
        url_imagem = row.get('imagem_principal_url')
        descricao = row.get('raw_description_snippet')

        if pd.isna(url_imagem) or not str(url_imagem).startswith('http'):
            falhas += 1
            continue

        # Cria um identificador único seguro
        id_seguro = limpar_nome_arquivo(f"{nome_cientifico}_{nome_popular}")
        nome_arquivo_img = f"{id_seguro}_{index}.jpg"
        nome_arquivo_txt = f"{id_seguro}_{index}.txt" # Padrão Kohya/Stable Diffusion
        
        caminho_img = os.path.join(imagens_dir, nome_arquivo_img)
        caminho_txt = os.path.join(imagens_dir, nome_arquivo_txt)

        # 1. Baixar e processar imagem
        if baixar_e_processar_imagem(url_imagem, caminho_img):
            
            # 2. Criar o "Par" (Arquivo de texto com o mesmo nome da imagem)
            # Dica: Enriquecemos o prompt com o nome científico para a IA aprender a associar
            prompt_treinamento = f"{nome_popular}, nome científico {nome_cientifico}. {limpar_descricao(descricao)}"
            
            with open(caminho_txt, 'w', encoding='utf-8') as f:
                f.write(prompt_treinamento)
            
            # 3. Salvar no metadado geral (formato JSONL é o padrão ouro para datasets)
            metadados.append({
                "file_name": nome_arquivo_img,
                "text": prompt_treinamento,
                "nome_popular": nome_popular,
                "nome_cientifico": nome_cientifico,
                "url_original": url_imagem
            })
            sucessos += 1
        else:
            falhas += 1

    # Salva o arquivo de metadados mestre
    with open(os.path.join(OUTPUT_DIR, "metadata.jsonl"), 'w', encoding='utf-8') as f:
        for item in metadados:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    print("\n" + "="*50)
    print(f"✅ CONCLUÍDO!")
    print(f"📸 Imagens processadas com sucesso: {sucessos}")
    print(f"❌ Falhas ao baixar: {falhas}")
    print(f"📁 Dataset salvo em: {os.path.abspath(OUTPUT_DIR)}")
    print("="*50)

if __name__ == "__main__":
    main()