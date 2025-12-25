import uuid
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from app.models import Product, ProductPatch
from app.repositories.factory import get_repository
from app.settings import PORT

app = FastAPI(title="Products API (CRUD + 3 storages)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# ——— CRUD ———

@app.post("/products", status_code=201, response_model=Product)
def create_product(p: Product):
    repo = get_repository()
    p.id = p.id or str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    p.created_at = now
    p.updated_at = now
    return repo.create(p)

@app.get("/products", response_model=list[Product])
def list_products():
    repo = get_repository()
    return repo.list_all()

@app.get("/products/{pid}", response_model=Product)
def get_product(pid: str):
    repo = get_repository()
    obj = repo.get(pid)
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    return obj

@app.patch("/products/{pid}", response_model=Product)
def patch_product(pid: str, patch: ProductPatch):
    repo = get_repository()
    updated = repo.patch(pid, patch)
    if not updated:
        raise HTTPException(status_code=404, detail="Not found")
    return updated

@app.delete("/products/{pid}", status_code=204)
def delete_product(pid: str):
    repo = get_repository()
    ok = repo.delete(pid)
    if not ok:
        raise HTTPException(status_code=404, detail="Not found")
    return Response(status_code=204)

# Явный OPTIONS (не обязателен — FastAPI и так отвечает)
@app.options("/products")
def options_products():
    return Response(headers={"Allow": "GET,POST,OPTIONS"})

@app.options("/products/{pid}")
def options_product_id():
    return Response(headers={"Allow": "GET,PATCH,DELETE,OPTIONS"})
