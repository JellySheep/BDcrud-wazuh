import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Optional
from datetime import datetime, timezone
from app.models import Product, ProductPatch
from .base import Repository

def _row_to_product(row) -> Product:
    return Product(
        id=str(row["id"]),
        name=row["name"],
        description=row.get("description") or "",
        price=float(row["price"]),
        qty=int(row["qty"]),
        category=row.get("category") or "",
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )

class PostgresRepository(Repository):
    def __init__(self, dsn: str):
        self._dsn = dsn
        # ленивые подключения — открываем по запросу

    def _conn(self):
        return psycopg2.connect(self._dsn, cursor_factory=RealDictCursor)

    def create(self, p: Product) -> Product:
        now = datetime.now(timezone.utc)
        p.created_at = now
        p.updated_at = now
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO products (id, name, description, price, qty, category, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, name, description, price, qty, category, created_at, updated_at
            """, (p.id, p.name, p.description, p.price, p.qty, p.category, p.created_at, p.updated_at))
            row = cur.fetchone()
            return _row_to_product(row)

    def get(self, id: str) -> Optional[Product]:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, description, price, qty, category, created_at, updated_at
                FROM products WHERE id = %s
            """, (id,))
            row = cur.fetchone()
            return _row_to_product(row) if row else None

    def list_all(self) -> List[Product]:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, description, price, qty, category, created_at, updated_at
                FROM products ORDER BY created_at DESC
            """)
            rows = cur.fetchall()
            return [_row_to_product(r) for r in rows]

    def patch(self, id: str, patch: ProductPatch) -> Optional[Product]:
        # Выбираем текущее
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM products WHERE id = %s", (id,))
            row = cur.fetchone()
            if not row:
                return None
            cur_p = _row_to_product(row)

            pd = patch.model_dump(exclude_unset=True)
            data = cur_p.model_dump()
            data.update({k: v for k, v in pd.items() if v is not None})
            data["id"] = id
            data["updated_at"] = datetime.now(timezone.utc)
            newp = Product(**data)

            cur.execute("""
                UPDATE products
                SET name=%s, description=%s, price=%s, qty=%s, category=%s, updated_at=%s
                WHERE id=%s
                RETURNING id, name, description, price, qty, category, created_at, updated_at
            """, (newp.name, newp.description, newp.price, newp.qty, newp.category,
                  newp.updated_at, id))
            row = cur.fetchone()
            return _row_to_product(row)

    def delete(self, id: str) -> bool:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM products WHERE id = %s", (id,))
            return cur.rowcount > 0
