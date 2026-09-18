from __future__ import annotations
import json
import os
from itertools import combinations
from pathlib import Path
from .catalog import ROOT, document

MODEL = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'

class SpeciesIndex:
    def __init__(self, path=ROOT/'data/index'):
        self.path = Path(path)
        self.model = None
        self.table = None
    def encoder(self):
        if self.model is None:
            os.environ.setdefault('USE_TF', '0')
            os.environ.setdefault('USE_FLAX', '0')
            os.environ.setdefault('HF_HOME', str(ROOT/'data/cache/huggingface'))
            from sentence_transformers import SentenceTransformer
            try:
                self.model = SentenceTransformer(MODEL, device='cpu', local_files_only=True)
            except OSError:
                self.model = SentenceTransformer(MODEL, device='cpu')
        return self.model
    def build(self, items):
        import lancedb
        self.path.mkdir(parents=True, exist_ok=True)
        vectors = self.encoder().encode([document(i) for i in items], normalize_embeddings=True, show_progress_bar=True)
        rows = [{'id': i['id'], 'text': document(i), 'url': i['url'], 'record': json.dumps(i, ensure_ascii=False), 'vector': v.tolist()} for i, v in zip(items, vectors)]
        self.table = lancedb.connect(str(self.path)).create_table('species', rows, mode='overwrite')
        (self.path/'metadata.json').write_text(json.dumps({'model': MODEL, 'count': len(rows), 'dimensions': len(vectors[0])}))
        return len(rows)
    def open(self):
        if self.table is None:
            import lancedb
            if not (self.path/'metadata.json').exists():
                raise RuntimeError('Índice ausente. Execute python -m aquarium.cli index')
            self.table = lancedb.connect(str(self.path)).open_table('species')
        return self.table
    def retrieve(self, ids):
        # Exact selected-ID retrieval avoids dropping rare species through top-k.
        if not ids or any(len(s) != 16 or any(c not in '0123456789abcdef' for c in s) for s in ids):
            raise ValueError('IDs inválidos')
        expr = 'id IN (' + ','.join("'"+s+"'" for s in ids) + ')'
        rows = self.open().search().where(expr).limit(len(ids)).to_list()
        by_id = {r['id']: json.loads(r['record']) for r in rows}
        missing = set(ids) - set(by_id)
        if missing:
            raise ValueError('Espécies desconhecidas: ' + ', '.join(sorted(missing)))
        return [by_id[s] for s in ids]
    def search(self, query, k=5, ids=None):
        vector = self.encoder().encode(query, normalize_embeddings=True).tolist()
        q = self.open().search(vector)
        if ids:
            if any(len(s) != 16 or any(c not in '0123456789abcdef' for c in s) for s in ids):
                raise ValueError('IDs inválidos')
            q = q.where('id IN (' + ','.join("'"+s+"'" for s in ids) + ')')
        return [{'id': r['id'], 'url': r['url'], 'text': r['text'], 'distance': r.get('_distance')} for r in q.limit(k).to_list()]


def compatibility(items):
    if not items:
        return {'status': 'compatible', 'warnings': [], 'ranges': {}, 'evidence': []}
    warnings, ranges = [], {}
    def warn(code, severity, message, species):
        warnings.append({'code': code, 'severity': severity, 'message': message, 'species': [i['id'] for i in species], 'sources': [i['url'] for i in species]})
    living = [i for i in items if i['kind'] != 'decoration']
    for key, label in [('ph', 'pH'), ('temperature', 'temperatura')]:
        available = [i for i in living if i['facts'][key] is not None]
        missing = [i for i in living if i['facts'][key] is None]
        if missing:
            warn('missing_'+key, 'unknown', f'{label}: ficha ausente ou suspeita para ' + ', '.join(i['name'] for i in missing), missing)
        if available:
            low = max(i['facts'][key][0] for i in available)
            high = min(i['facts'][key][1] for i in available)
            ranges[key] = {'min': low, 'max': high, 'complete': not missing, 'overlap': low <= high}
            if low > high:
                warn('disjoint_'+key, 'block', f'Sem faixa comum de {label}: limite inferior {low} supera limite superior {high}.', available)
    for i in living:
        unknown = []
        if not i['facts']['water']: unknown.append('tipo de água/salinidade')
        if i['kind'] in ('fish', 'shrimp'):
            for key, label in [('temperament', 'temperamento'), ('diet', 'alimentação'), ('size_cm', 'tamanho adulto')]:
                if i['facts'][key] is None: unknown.append(label)
        if unknown:
            warn('incomplete_facts', 'unknown', f'{i["name"]}: confirmar ' + ', '.join(unknown) + '.', [i])
    for a, b in combinations(living, 2):
        fa, fb = a['facts'], b['facts']
        if fa['water'] and fb['water'] and not set(fa['water']) & set(fb['water']):
            warn('water_conflict', 'block', f'{a["name"]} e {b["name"]}: tipos de água incompatíveis.', [a,b])
        if a['kind'] == 'plant' or b['kind'] == 'plant':
            animal = b if a['kind'] == 'plant' else a
            if animal['kind'] == 'fish' and animal['facts']['diet'] == 'herbivore':
                warn('plant_grazing', 'review', f'{animal["name"]} pode consumir plantas; validar espécie e manejo.', [a,b])
            continue
        if 'risk' in (fa['temperament'], fb['temperament']):
            warn('temperament_risk', 'review', f'{a["name"]} × {b["name"]}: comportamento agressivo/territorial descrito na ficha.', [a,b])
        for predator, prey in ((a,b),(b,a)):
            fp, fs = predator['facts'], prey['facts']
            if fp['size_cm'] and fs['size_cm'] and fp['size_cm'] >= 3*fs['size_cm'] and fp['diet'] in ('carnivore', 'omnivore'):
                warn('predation_risk', 'review', f'{predator["name"]} pode predar {prey["name"]}; diferença de tamanho ≥3×. Heurística, confirmar anatomia e comportamento.', [predator,prey])
    status = 'incompatible' if any(w['severity']=='block' for w in warnings) else 'uncertain' if warnings else 'compatible'
    return {'status': status, 'warnings': warnings, 'ranges': ranges, 'evidence': [{'id': i['id'], 'url': i['url'], 'facts': i['facts'], 'issues': i['issues']} for i in items], 'scope': 'Triagem baseada nas fichas; não avalia volume, lotação, sexo, GH/KH, reprodução ou tamanho de cardume.'}


def evaluate(index, ids):
    if not ids:
        return compatibility([])
    selected = index.retrieve(list(dict.fromkeys(ids)))
    answer = compatibility(selected)
    answer['retrieved'] = index.search('Compatibilidade: pH temperatura água salobra doce agressividade territorial alimentação tamanho adulto', k=len(selected), ids=[i['id'] for i in selected])
    return answer
