from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from database import Base

# Таблица пользователей
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    login = Column(String, unique=True, index=True)
    password = Column(String)  # В реальном проекте тут хранят хеш!
    role = Column(String, default="user") # 'user' или 'admin'

# Таблица логов (ЛР6)
class Log(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, index=True)
    user_login = Column(String)
    action = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

# Таблица товаров (для ЛР3, если будем хранить их в БД)
class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    brand = Column(String)
    price = Column(Integer)
    image_url = Column(String)
    category = Column(String)
