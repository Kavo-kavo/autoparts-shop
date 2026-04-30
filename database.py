import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# 1. Пытаемся найти настройки облачной базы (Vercel или Render)
# 2. Если их нет, используем твой локальный адрес
DB_URL = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL") or "postgresql://postgres:1212@localhost/autoparts_db"

# Исправление для Vercel/Render (они дают ссылку postgres://, а питону нужно postgresql://)
if DB_URL and DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

# Настройка SSL (обязательна для облачных баз)
connect_args = {}
if "neon.tech" in DB_URL or "vercel" in DB_URL or "render" in DB_URL:
    connect_args = {"sslmode": "require"}

engine = create_engine(DB_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()