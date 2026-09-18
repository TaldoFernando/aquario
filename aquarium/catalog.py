from __future__ import annotations
import hashlib
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TECHNICAL = ('nome_popular', 'nome_cientifico', 'ph', 'temperatura_ideal', 'sociabilidade', 'alimentacao', 'tamanho_adulto', 'origem', 'familia', 'iluminacao', 'co2')


def fold(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(text or '').lower()) if not unicodedata.combining(c))


def stable_id(item):
    return hashlib.sha256(item['url'].encode()).hexdigest()[:16]


def load_catalog(path=ROOT / 'kauar_peixes.json'):
    records = json.loads(Path(path).read_text())
    if not isinstance(records, list):
        raise ValueError('O catálogo deve ser uma lista JSON.')
    seen, result = set(), []
    for raw in records:
        sid = stable_id(raw)
        if sid in seen:
            continue
        seen.add(sid)
        name = raw.get('nome_popular') or raw['url'].split('/')[-1]
        text = fold(name)
        kind = ('shrimp' if 'camarao' in text else 'plant' if raw.get('tipo') == 'planta_ou_aquascape' and raw.get('nome_cientifico') else 'decoration' if raw.get('tipo') == 'planta_ou_aquascape' else 'fish')
        eligible = bool(raw.get('imagem_principal_url')) and not any(s in text for s in ('compra de cardume', 'compre ', 'leve ', 'kit '))
        facts, issues = {}, []
        for key, lo, hi, bounds in [('ph', 'ph_min', 'ph_max', (0, 14)), ('temperature', 'temp_min_c', 'temp_max_c', (10, 40))]:
            a, b = raw.get(lo), raw.get(hi)
            if isinstance(a, (float, int)) and isinstance(b, (float, int)) and bounds[0] <= a <= b <= bounds[1]:
                if a == b:
                    facts[key] = None
                    issues.append(f'{key}: valor pontual não estabelece faixa de tolerância; verificar fonte')
                else:
                    facts[key] = [a, b]
            else:
                facts[key] = None
                issues.append(f'{key}: ausente ou fora dos limites de triagem; verificar fonte')
        # Do not infer freshwater from the category URL: brackish species occur there.
        source_text = fold(' '.join(str(raw.get(k) or '') for k in ('origem', 'raw_description_snippet')))
        waters = set()
        if 'salobr' in source_text:
            waters.add('brackish')
        if 'agua doce' in source_text:
            waters.add('fresh')
        if 'agua salgada' in source_text or 'marinh' in source_text:
            waters.add('marine')
        facts['water'] = sorted(waters) if len(waters) == 1 else None
        if len(waters) > 1:
            issues.append('Tipo de água ambíguo: texto menciona mais de um regime de salinidade')
        social = fold(raw.get('sociabilidade'))
        facts['temperament'] = ('risk' if re.search(r'agressiv|territorial|predador', social) and not re.search(r'nao\s+(?:e\s+)?agressiv|sem\s+agressiv', social) else 'peaceful' if re.search(r'pacific|tranquil', social) else None)
        food = fold(raw.get('alimentacao'))
        facts['diet'] = 'carnivore' if 'carnivor' in food else 'omnivore' if 'onivor' in food else 'herbivore' if 'herbivor' in food else None
        size = fold(raw.get('tamanho_adulto'))
        nums = re.findall(r'(\d+(?:[.,]\d+)?)\s*(?:a\s*\d+(?:[.,]\d+)?)?\s*cm', size)
        all_nums = re.findall(r'\d+(?:[.,]\d+)?', size) if nums else []
        facts['size_cm'] = max(map(lambda n: float(n.replace(',', '.')), all_nums), default=None)
        result.append({'id': sid, 'name': name, 'scientific_name': raw.get('nome_cientifico'), 'kind': kind, 'eligible': eligible, 'url': raw['url'], 'image_url': raw.get('imagem_principal_url'), 'facts': facts, 'issues': issues, 'raw': raw})
    return result


def document(item):
    fields = '\n'.join(f'{k}: {item["raw"].get(k) or "não informado"}' for k in TECHNICAL)
    return fields + '\nParâmetros validados: ' + json.dumps(item['facts'], ensure_ascii=False) + '\nIncertezas: ' + '; '.join(item['issues'])
