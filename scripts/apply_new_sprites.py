from __future__ import annotations
import hashlib, json, shutil, unicodedata, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'pixel_artes_kauar_atualizado'
ASSETS = ROOT / 'extension' / 'assets'
CATALOG = ROOT / 'extension' / 'assets' / 'catalog.json'

def fold(s):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', str(s or '').lower()) if not unicodedata.combining(c)).split())

def sha16(text):
    return hashlib.sha256(text.encode()).hexdigest()[:16]

# delivered descriptive PNG -> species common name (as in relacao_pixelarts.json)
# NOTE: model has no vision; pairs are inferred from filename semantics + color
# profiles. UNCERTAIN pairs are marked below and should be eyeballed in popup.html.
MAP = {
    # --- peixes ---
    'peixe_agulha_em_pixel_art.png': 'Agulhinha Comum',
    'peixe_agulha_em_pixel_art_retro.png': 'Agulhinha Prata',
    'peixe_prata_pixel_art_em_perfil.png': 'Balashark',                 # UNCERTAIN (silver)
    'peixe_pixelado_de_cauda_vermelha.png': 'Botia Blue Red Tail',      # UNCERTAIN (dark+red)
    'peixe_loach_pixelado_turquesa.png': 'Botia Lohachata Yoyo',
    'peixe_gobí_em_pixel_art_retrô.png': 'Goby Dardo',
    'peixe_gobí_listrado_em_pixel_art.png': 'Pseudomugil  Luminatus',   # UNCERTAIN (only spare fish)
    'peixe_preto_com_nadadeiras_rubras.png': 'Labeo Bicolor',
    'peixe_albino_pixelado_com_barbatanas_vermelhas.png': 'Labeo Frenatus Albino',
    'peixe_pixelado_albino_com_nadadeiras_laranjas.png': 'Trewavasae Red Top Albino',
    'peixe_azul_de_crista_vermelha_em_pixel_art.png': 'Trewavasae Red Top',  # blue+red crest
    'peixe_arco_íris_em_pixel_art.png': 'Melanotaenia Lacustri',
    'peixe_arco_íris_neon_em_pixel_art.png': 'Melanotaenia Blue Neon Anã',
    'peixe_arco_íris_dourado_em_pixel_art.png': 'Melanotaenia Trifasciata Gold',
    'peixe_arco_íris_pixelado_dourado.png': 'Melanotaenia Maçã',        # UNCERTAIN
    'peixe_lápis_pixel_art_retrô.png': 'Peixe Lápis',
    'peixe_paraíso_albino_em_pixel_art.png': 'Peixe Paraíso Albino',
    'peixe_paraíso_em_pixel_art_retro.png': 'Peixe Paraíso',
    'peixe_transparente_iridescente_em_pixel_art.png': 'Tetra Vidro',
    'peixe_ciclídeo_pixelado_vibrante.png': 'Aulonocara Fire Fish',
    'peixe_pixelado_listrado_em_perfil.png': 'Barbo Five Banded',       # UNCERTAIN (striped)
    'sprite_pixelado_de_barbo_cereja.png': 'Barbo Conchônio Cereja',
    'peixe_pixelado_denison_colorido.png': 'Barbus Denisoni Gold',
    'peixe_pixel_art_com_listras_vermelhas_e_pretas.png': 'Barbo Denisoni',  # UNCERTAIN (red/black stripes)
    'peixe_barbado_dourado_em_pixel_art.png': 'Barbus Ouro',
    'barbo_tigre_em_pixel_art.png': 'Barbus Sumatra',
    'peixe_tigre_pixel_art_em_fundo_transparente.png': 'Barbus Sumatra Verde',
    'peixe_pixel_art_vermelho_em_sprite.png': 'Barbo Titeia Super Red',
    'peixe_pixelado_vermelho_em_perfil.png': 'Barbo Titeia Albino Super Red',  # UNCERTAIN (pale red)
    # --- camarões ---
    'camarão_pixel_art_translúcido_em_perfil.png': 'Nano Camarão Filtrador',
    'camarão_preto_pixelado_em_perfil.png': 'Camarão Black Sakura',
    'camarão_azul_em_pixel_art.png': 'Camarão Blue Fantasy Dream',
    'sprite_de_camarão_laranja_pixelado.png': 'Camarão Orange Sakura',
    'camarão_sakura_vermelho_em_pixel_art.png': 'Camarão Red Sakura',
    'camarão_amarelo_em_pixel_art.png': 'Camarão Yellow',
    # --- plantas (delivered filename == pixel_art_file) ---
    'jiboia_pixelada_com_raízes_expostas.png': 'Jiboia',
    'tufo_de_grama_em_pixel_art.png': 'Grama Alta',
    'planta_anubias_pixelada_com_raízes.png': 'Anubia barteri Coffeefolia',
    'planta_aquática_pixelada_com_raízes_douradas.png': 'Echinodorus amazonicus',
}

def main():
    ASSETS.mkdir(exist_ok=True)
    catalog = json.loads(CATALOG.read_text())
    rel = json.loads((ROOT / 'relacao_pixelarts.json').read_text())
    srcs = {fold(f.name): f for f in FOLDER.glob('*.png')}
    by_name = {fold(i['name']): i for i in catalog}
    rel_by_name = {fold(r['nome_popular']): r for r in rel}

    report, problems = [], []
    for fname, common in MAP.items():
        src = srcs.get(fold(fname))
        if src is None:
            problems.append(f'source missing: {fname}'); continue
        rec = rel_by_name.get(fold(common))
        if rec is None:
            problems.append(f'species missing: {common}'); continue
        is_plant = rec.get('tipo') == 'planta'
        if is_plant:
            item = by_name.get(fold(common))
            if item is None:
                item = {
                    'id': sha16('kauar-plant:' + common),
                    'name': common,
                    'scientific_name': rec.get('nome_cientifico'),
                    'kind': 'plant',
                    'facts': {'ph': [rec['ph_min'], rec['ph_max']] if rec.get('ph_min') and rec.get('ph_max') else None,
                              'temperature': [rec['temp_min_c'], rec['temp_max_c']] if rec.get('temp_min_c') and rec.get('temp_max_c') else None,
                              'water': None, 'temperament': None, 'diet': None, 'size_cm': None},
                    'issues': [],
                    'url': None,
                    'sprite': None,
                }
                catalog.append(item)
                by_name[fold(common)] = item
        else:
            item = by_name.get(fold(common))
            if item is None:
                problems.append(f'catalog species missing: {common}'); continue
        target = ASSETS / f"{item['id']}.png"
        shutil.copyfile(src, target)
        item['sprite'] = f"assets/{item['id']}.png"
        report.append({'species': common, 'kind': item['kind'], 'sprite_file': src.name, 'asset': target.name})

    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=1))
    (ROOT / 'config' / 'new_sprite_assets.json').write_text(json.dumps(report, ensure_ascii=False, indent=1))

    used = {fold(x['sprite_file']) for x in report}
    unassigned = sorted(f.name for f in FOLDER.glob('*.png') if fold(f.name) not in used)
    print(f'mapped={len(report)} plants_added={sum(1 for x in report if x["kind"]=="plant")}')
    print('problems:', problems or 'none')
    print('unassigned delivered pngs:')
    for u in unassigned:
        print('  ', u)

if __name__ == '__main__':
    main()