from pymongo import MongoClient
from pymongo.collection import Collection
from typing import List, Optional
from datetime import datetime, timezone
from app.models import Product, ProductPatch
from .base import Repository

def _doc_to_product(doc) -> Product:
    return Product(
        id=str(doc["id"]),
        name=doc["name"],
        description=doc.get("description") or "",
        price=float(doc["price"]),
        qty=int(doc["qty"]),
        category=doc.get("category") or "",
        created_at=doc.get("created_at"),
        updated_at=doc.get("updated_at"),
    )

class MongoRepository(Repository):
    def __init__(self, uri: str, dbname: str, coll: str):
        self._client = MongoClient(uri)
        self._coll: Collection = self._client[dbname][coll]
        self._coll.create_index("id", unique=True)

    def create(self, p: Product) -> Product:
        now = datetime.now(timezone.utc)
        p.created_at = now
        p.updated_at = now
        self._coll.insert_one(p.model_dump())
        return p

    def get(self, id: str) -> Optional[Product]:
        doc = self._coll.find_one({"id": id})
        return _doc_to_product(doc) if doc else None

    def list_all(self) -> List[Product]:
        docs = self._coll.find().sort("created_at", -1)
        return [_doc_to_product(d) for d in docs]

    def patch(self, id: str, patch: ProductPatch) -> Optional[Product]:
        upd = {k: v for k, v in patch.model_dump(exclude_unset=True).items() if v is not None}
        if not upd:
            doc = self._coll.find_one({"id": id})
            return _doc_to_product(doc) if doc else None
        upd["updated_at"] = datetime.now(timezone.utc)
        doc = self._coll.find_one_and_update(
            {"id": id},
            {"$set": upd},
            return_document=True
        )
        return _doc_to_product(doc) if doc else None

    def delete(self, id: str) -> bool:
        res = self._coll.delete_one({"id": id})
        return res.deleted_count > 0
