import json
import pandas as pd
import re
import os

def extrair_caracteristicas_visuais(descricao, nome_popular, nome_cientifico):
    """Extrai características visuais específicas da descrição."""
    caracteristicas = []
    full_text = f"{str(descricao).lower()} {str(nome_popular).lower()} {str(nome_cientifico).lower()}"
    
    # Cores e padrões
    if any(c in full_text for c in ['amarelo', 'listra', 'preta', 'abelha', 'bumblebee']):
        caracteristicas.append("yellow body with black vertical stripes")
    if any(c in full_text for c in ['vermelho', 'red', 'sakura', 'cherry']):
        caracteristicas.append("bright red segmented body")
    if any(c in full_text for c in ['prateado', 'prata', 'silver']):
        caracteristicas.append("silvery metallic body")
    if any(c in full_text for c in ['preto', 'black', 'escuro', 'carbon']):
        caracteristicas.append("dark body coloration")
    if any(c in full_text for c in ['verde', 'green']):
        caracteristicas.append("green tones")
    if any(c in full_text for c in ['azul', 'blue']):
        caracteristicas.append("blue iridescent scales")
    if any(c in full_text for c in ['laranja', 'orange']):
        caracteristicas.append("orange coloration")
    if any(c in full_text for c in ['branco', 'white', 'albino']):
        caracteristicas.append("white or albino coloration")
    
    # Características físicas específicas
    if any(c in full_text for c in ['agulha', 'halfbeak', 'bico', 'pontiagudo', 'dermogenys']):
        caracteristicas.append("elongated lower jaw, needle-like appearance")
    if any(c in full_text for c in ['tubarão', 'shark', 'balashark', 'balantiocheilos']):
        caracteristicas.append("triangular dorsal fin, shark-like body shape, silver body with black-edged fins")
    if any(c in full_text for c in ['nadadeira', 'cauda', 'fan', 'leque', 'veil']):
        caracteristicas.append("prominent flowing fins")
    if any(c in full_text for c in ['listra', 'stripe', 'zebra', 'zebrinus']):
        caracteristicas.append("striped pattern")
    if any(c in full_text for c in ['mancha', 'spot', 'ponto', 'maculatus']):
        caracteristicas.append("spotted pattern")
    
    # Tamanho
    if 'cm' in full_text:
        if any(x in full_text for x in ['2', '3', '4', 'pequeno', 'small', '4,5']):
            caracteristicas.append("small sized (2-4cm)")
        elif any(x in full_text for x in ['5', '6', '7', 'médio', 'medium']):
            caracteristicas.append("medium sized (5-7cm)")
        elif any(x in full_text for x in ['10', '15', '20', '30', '35', 'grande', 'large']):
            caracteristicas.append("large sized (10-35cm)")
    
    return ", ".join(caracteristicas) if caracteristicas else "distinctive ornamental features"

def gerar_prompt_peixe(row):
    nome_popular = str(row.get('nome_popular', 'Fish'))
    nome_cientifico = str(row.get('nome_cientifico', ''))
    descricao = row.get('raw_description_snippet', '')
    caracteristicas = extrair_caracteristicas_visuais(descricao, nome_popular, nome_cientifico)
    
    return f"""Convert the subject of the reference product photograph into a game-ready aquarium pixel-art sprite: {nome_popular} ({nome_cientifico}). Preserve {caracteristicas}, streamlined fish body, fins and tail. Exactly one fish in horizontal side view facing RIGHT. Remove all photographic background. True transparent RGBA background. Center entire subject with 12% margin, no cropping. Unified 16-bit cozy aquarium game art direction: chunky square pixels, art designed on a 96 by 96 logical pixel grid and enlarged with nearest-neighbor only; 1 logical pixel dark navy outer contour (#172c3c), hard stepped edges, no antialiasing, no gradient, no dither. Consistent illumination from upper LEFT, small cream highlights and navy shadows. Limited palette navy #172c3c, slate #40576b, cream #f4e5bd, ochre #e5b54a, yellow #f5d76e, red #dc5045, dark red #923747, coral #ee8a65, dark green #235343, green #36865a, leaf #78ad63, pale green #b0cd79, turquoise #62c5be. No text, no lettering, no watermark, no ground shadow. This must be an actual crisp pixel art sprite, not a pixelated photograph."""

def gerar_prompt_camarao(row):
    nome_popular = str(row.get('nome_popular', 'Shrimp'))
    nome_cientifico = str(row.get('nome_cientifico', ''))
    descricao = row.get('raw_description_snippet', '')
    caracteristicas = extrair_caracteristicas_visuais(descricao, nome_popular, nome_cientifico)
    
    return f"""Convert the subject of the reference product photograph into a game-ready aquarium pixel-art sprite: {nome_popular} ({nome_cientifico}). Preserve {caracteristicas}, segmented shell, tiny legs and two long antennae. Exactly one shrimp in horizontal side view facing RIGHT. Remove all photographic background. True transparent RGBA background. Center entire subject with 12% margin, no cropping. Unified 16-bit cozy aquarium game art direction: chunky square pixels, art designed on a 96 by 96 logical pixel grid and enlarged with nearest-neighbor only; 1 logical pixel dark navy outer contour (#172c3c), hard stepped edges, no antialiasing, no gradient, no dither. Consistent illumination from upper LEFT, small cream highlights and navy shadows. Limited palette navy #172c3c, slate #40576b, cream #f4e5bd, ochre #e5b54a, yellow #f5d76e, red #dc5045, dark red #923747, coral #ee8a65, dark green #235343, green #36865a, leaf #78ad63, pale green #b0cd79, turquoise #62c5be. No text, no lettering, no watermark, no ground shadow. This must be an actual crisp pixel art sprite, not a pixelated photograph."""

def gerar_prompt_planta(row):
    nome_popular = str(row.get('nome_popular', 'Aquatic Plant'))
    nome_cientifico = str(row.get('nome_cientifico', ''))
    
    return f"""Convert the subject of the reference product photograph into a game-ready aquarium pixel-art sprite: {nome_popular} ({nome_cientifico}). Preserve natural leaf shapes, stems and root structure. Exactly one plant specimen centered. Remove all photographic background. True transparent RGBA background. Center entire subject with 12% margin, no cropping. Unified 16-bit cozy aquarium game art direction: chunky square pixels, art designed on a 96 by 96 logical pixel grid and enlarged with nearest-neighbor only; 1 logical pixel dark navy outer contour (#172c3c), hard stepped edges, no antialiasing, no gradient, no dither. Consistent illumination from upper LEFT, small cream highlights and navy shadows. Limited palette navy #172c3c, slate #40576b, cream #f4e5bd, ochre #e5b54a, yellow #f5d76e, red #dc5045, dark red #923747, coral #ee8a65, dark green #235343, green #36865a, leaf #78ad63, pale green #b0cd79, turquoise #62c5be. No text, no lettering, no watermark, no ground shadow. This must be an actual crisp pixel art sprite, not a pixelated photograph."""

def gerar_prompt_ampularia(row):
    nome_popular = str(row.get('nome_popular', 'Mystery Snail'))
    nome_cientifico = str(row.get('nome_cientifico', ''))
    descricao = row.get('raw_description_snippet', '')
    caracteristicas = extrair_caracteristicas_visuais(descricao, nome_popular, nome_cientifico)
    
    return f"""Convert the subject of the reference product photograph into a game-ready aquarium pixel-art sprite: {nome_popular} ({nome_cientifico}). Preserve {caracteristicas}, spiral shell, soft body and antennae. Exactly one snail in side view. Remove all photographic background. True transparent RGBA background. Center entire subject with 12% margin, no cropping. Unified 16-bit cozy aquarium game art direction: chunky square pixels, art designed on a 96 by 96 logical pixel grid and enlarged with nearest-neighbor only; 1 logical pixel dark navy outer contour (#172c3c), hard stepped edges, no antialiasing, no gradient, no dither. Consistent illumination from upper LEFT, small cream highlights and navy shadows. Limited palette navy #172c3c, slate #40576b, cream #f4e5bd, ochre #e5b54a, yellow #f5d76e, red #dc5045, dark red #923747, coral #ee8a65, dark green #235343, green #36865a, leaf #78ad63, pale green #b0cd79, turquoise #62c5be. No text, no lettering, no watermark, no ground shadow. This must be an actual crisp pixel art sprite, not a pixelated photograph."""

def classificar_tipo_robusto(row):
    """Classificação robusta baseada em dicionário biológico de aquarismo."""
    nome_popular = str(row.get('nome_popular', '')).lower()
    nome_cientifico = str(row.get('nome_cientifico', '')).lower()
    descricao = str(row.get('raw_description_snippet', '')).lower()
    
    # Combina tudo para busca
    full_text = f"{nome_popular} {nome_cientifico} {descricao}"

    # Regra de ouro: Se o nome popular começa com "Peixe", é peixe.
    if nome_popular.startswith('peixe') or 'fish' in nome_popular:
        return 'peixe'

    # 1. PLANTAS
    plant_keywords = ['anubia', 'anubias', 'musgo', 'moss', 'java fern', 'microsorum', 
                      'vallisneria', 'echinodorus', 'amazon sword', 'cryptocoryne', 'crypt',
                      'riccia', 'marsilea', 'ludwigia', 'rotala', 'bacopa', 'hygrophila',
                      'eleocharis', 'hairgrass', 'glossostigma', 'hemianthus', 'cuba',
                      'lilaeopsis', 'pogostemon', 'taxiphyllum', 'fontinalis', 'vesicularia',
                      'ricciocarpus', 'salvinia', 'azolla', 'lemna', 'duckweed',
                      'ceratophyllum', 'hornwort', 'myriophyllum', 'cabomba', 'limnophila',
                      'hydrocotyle', 'alternanthera', 'mayaca', 'saururus', 'aponogeton',
                      'crinum', 'lagenandra', 'bucephalandra', 'bolbitis', 'ceratopteris',
                      'planta', 'plant', 'flora']
    if any(kw in full_text for kw in plant_keywords):
        return 'planta'

    # 2. AMPULÁRIAS / CARACÓIS
    snail_keywords = ['ampularia', 'ampullaria', 'pomacea', 'neritina', 'nerite', 'neritidae',
                      'melanoides', 'physa', 'planorbis', 'anentome', 'asolene', 'cipangopaludina',
                      'caracol', 'snail', 'escargot', 'apple snail', 'mystery snail', 'ramshorn',
                      'bladder snail', 'trumpet snail', 'assassin snail', 'caracol assassino',
                      'caracol trombeta', 'caracol maçã']
    if any(kw in full_text for kw in snail_keywords):
        return 'ampularia'

    # 3. CAMARÕES
    shrimp_keywords = ['camarao', 'camarão', 'shrimp', 'neocaridina', 'caridina', 'atya',
                       'macrobrachium', 'palaemon', 'cherry', 'amano', 'yamato', 'bamboo',
                       'vampire', 'crystal', 'bee', 'tiger', 'ghost', 'ghost shrimp',
                       'red cherry', 'sakura', 'blue dream', 'blue velvet', 'orange sakura',
                       'yellow neon', 'black rose', 'carbon', 'panda', 'habana', 'fire',
                       'caridea']
    if any(kw in full_text for kw in shrimp_keywords):
        return 'camarao'

    # 4. PEIXES (Fallback padrão para aquários)
    return 'peixe'

def main():
    INPUT_FILE = '/Users/fernandodavilalbcfilho/Downloads/aquario/kauar_peixes.json'
    OUTPUT_DIR = '/Users/fernandodavilalbcfilho/Downloads/aquario'
    OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'prompts_pixel_art.json')
    
    print(f"📖 Lendo {INPUT_FILE}...")
    
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Erro: Arquivo não encontrado em {INPUT_FILE}")
        return
    
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            df = pd.DataFrame(json.load(f))
    except Exception as e:
        print(f"❌ Erro ao ler arquivo: {e}")
        return
    
    prompts = []
    print(f" Gerando prompts para {len(df)} espécies...\n")
    
    for idx, row in df.iterrows():
        nome_popular = row.get('nome_popular', 'Unknown')
        nome_cientifico = row.get('nome_cientifico', '')
        url = row.get('imagem_principal_url', '')
        
        # Classificação Robusta
        categoria = classificar_tipo_robusto(row)
        
        if categoria == 'camarao':
            prompt = gerar_prompt_camarao(row)
        elif categoria == 'planta':
            prompt = gerar_prompt_planta(row)
        elif categoria == 'ampularia':
            prompt = gerar_prompt_ampularia(row)
        else:
            prompt = gerar_prompt_peixe(row)
        
        prompts.append({
            "id": idx,
            "nome_popular": nome_popular,
            "nome_cientifico": nome_cientifico,
            "categoria": categoria,
            "url_referencia": url,
            "prompt_pixel_art": prompt.strip()
        })
        
        print(f"✓ [{categoria.upper():8}] {nome_popular} ({nome_cientifico})")
    
    output_data = {
        "total_prompts": len(prompts),
        "paleta_cores": {
            "navy": "#172c3c", "slate": "#40576b", "cream": "#f4e5bd", "ochre": "#e5b54a",
            "yellow": "#f5d76e", "red": "#dc5045", "dark_red": "#923747", "coral": "#ee8a65",
            "dark_green": "#235343", "green": "#36865a", "leaf": "#78ad63", "pale_green": "#b0cd79",
            "turquoise": "#62c5be"
        },
        "especificacoes_tecnicas": {
            "grid": "96x96 pixels", "estilo": "16-bit chunky pixel art",
            "iluminacao": "superior esquerda", "contorno": "1px navy (#172c3c)",
            "orientacao": "vista lateral horizontal, virado para direita", "fundo": "transparente RGBA"
        },
        "prompts": prompts
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"✅ CONCLUÍDO!")
    print(f"📝 Total de prompts gerados: {len(prompts)}")
    print(f"📁 Arquivo salvo: {OUTPUT_FILE}")
    print(f"\n📊 Distribuição por categoria:")
    
    categorias = {}
    for p in prompts:
        cat = p['categoria']
        categorias[cat] = categorias.get(cat, 0) + 1
    
    for cat, count in sorted(categorias.items()):
        print(f"   • {cat.capitalize()}: {count}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()