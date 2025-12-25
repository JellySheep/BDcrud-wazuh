from app.settings import STORAGE, POSTGRES_DSN, MONGO_DSN, MONGO_DB, MONGO_COLL
from .base import Repository
from .memory import MemoryRepository
from .postgres import PostgresRepository
from .mongo import MongoRepository

# единый синглтон для memory
_MEM = None

def get_repository() -> Repository:
    global _MEM
    if STORAGE in ("memory", "fake"):
        if _MEM is None:
            _MEM = MemoryRepository()
        return _MEM
    elif STORAGE == "postgres":
        return PostgresRepository(POSTGRES_DSN)
    elif STORAGE == "mongo":
        return MongoRepository(MONGO_DSN, MONGO_DB, MONGO_COLL)
    else:
        # дефолт — memory
        if _MEM is None:
            _MEM = MemoryRepository()
        return _MEM
