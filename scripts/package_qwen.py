"""Build portable runner bundle without environments, weights or private files."""
import json
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
ROOT=Path(__file__).resolve().parents[1]
FILES=['aquarium/__init__.py','aquarium/catalog.py','aquarium/sprites.py','aquarium/qwen_pixelart.py','scripts/qwen_pixelart.py','requirements-qwen.txt','config/style.json','config/smoke.json','config/qwen_pixelart.json','kauar_peixes.json','notebooks/Qwen_Pixel_Art.ipynb','docs/QWEN_PIXELART.md']
for item in json.loads((ROOT/'config/smoke.json').read_text()):
    FILES += ['data/sources/'+item['id']+'.png','data/sources/'+item['id']+'.json']
out=ROOT/'dist/aquario-qwen.zip';out.parent.mkdir(exist_ok=True)
with ZipFile(out,'w',ZIP_DEFLATED) as z:
    for name in FILES:z.write(ROOT/name,name)
    z.write(ROOT/'docs/QWEN_PIXELART.md','README.md')
print(out, out.stat().st_size, 'bytes')
