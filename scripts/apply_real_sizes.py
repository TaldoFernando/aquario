from __future__ import annotations
import json, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'extension' / 'assets' / 'catalog.json'
SIZES = ROOT / 'config' / 'species_sizes_cm.json'

def fold(s):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', str(s or '').lower()) if not unicodedata.combining(c)).split())

def main():
    sizes = {fold(k): v for k, v in json.loads(SIZES.read_text()).items()}
    catalog = json.loads(CATALOG.read_text())
    hit, miss = 0, []
    for item in catalog:
        key = fold(item['name'])
        if key in sizes:
            item['facts']['size_cm'] = sizes[key]
            hit += 1
    for k in sizes:
        if not any(fold(i['name']) == k for i in catalog):
            miss.append(k)
    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=1))
    print(f'updated {hit} items; unmatched: {miss or "none"}')

if __name__ == '__main__':
    main()
