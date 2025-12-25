import os

PORT = int(os.getenv("PORT", "8000"))
STORAGE = os.getenv("STORAGE", "memory").lower()

# Postgres DSN (для psycopg2)
POSTGRES_DSN = os.getenv(
    "POSTGRES_DSN",
    "postgres://postgres:postgres@localhost:5432/postgres"
)

# Mongo
MONGO_DSN = os.getenv("MONGO_DSN", "mongodb://localhost:27017")
MONGO_DB  = os.getenv("MONGO_DB", "testdb")
MONGO_COLL = os.getenv("MONGO_COLL", "products")
