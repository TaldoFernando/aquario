from __future__ import annotations
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from .catalog import load_catalog
from .rag import SpeciesIndex, evaluate

app = FastAPI(title='Aquário local', version='0.1.0')
index = SpeciesIndex()

class Selection(BaseModel):
    ids: list[str] = Field(default_factory=list, max_length=60)

@app.get('/health')
def health():
    return {'ok': True, 'index_ready': (index.path/'metadata.json').exists()}

@app.get('/species')
def species():
    return [{k:v for k,v in i.items() if k != 'raw'} for i in load_catalog() if i['eligible']]

@app.get('/search')
def search(q: str):
    if not 1 <= len(q) <= 500:
        raise HTTPException(422, 'Consulta deve conter 1–500 caracteres')
    try:
        return index.search(q)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))

@app.post('/compatibility')
def check(selection: Selection):
    try:
        return evaluate(index, selection.ids)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))
