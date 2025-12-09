import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

DB_URL = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL") or "postgresql://postgres:1212@localhost/autoparts_db"

if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

connect_args = {}
if "vercel-storage" in DB_URL or "neon.tech" in DB_URL:
    connect_args = {"sslmode": "require"}

engine = create_engine(DB_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()