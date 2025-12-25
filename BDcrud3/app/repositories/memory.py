from typing import List, Optional
from threading import RLock
from datetime import datetime
from app.models import Product, ProductPatch
from .base import Repository

class MemoryRepository(Repository):
    def __init__(self):
        self._store = {}  # id -> Product
        self._lock = RLock()

    def create(self, p: Product) -> Product:
        with self._lock:
            self._store[p.id] = p
            return p

    def get(self, id: str) -> Optional[Product]:
        return self._store.get(id)

    def list_all(self) -> List[Product]:
        return list(self._store.values())

    def patch(self, id: str, patch: ProductPatch) -> Optional[Product]:
        with self._lock:
            cur = self._store.get(id)
            if not cur:
                return None
            data = cur.model_dump()
            pd = patch.model_dump(exclude_unset=True)
            data.update({k: v for k, v in pd.items() if v is not None})
            data["id"] = id
            data["updated_at"] = datetime.utcnow()
            updated = Product(**data)
            self._store[id] = updated
            return updated

    def delete(self, id: str) -> bool:
        with self._lock:
            return self._store.pop(id, None) is not None
