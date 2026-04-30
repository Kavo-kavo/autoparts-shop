import os
import sys
from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
import csv
import io
from fastapi import UploadFile, File

# Добавляем путь к текущей папке для импортов
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import models
from database import SessionLocal, engine

# Создаем таблицы в БД
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Схемы данных ---
class UserCreate(BaseModel):
    login: str
    password: str

class UserLogin(BaseModel):
    login: str
    password: str

class LogCreate(BaseModel):
    user_login: str
    action: str

class ProductCreate(BaseModel):
    name: str
    brand: str
    price: int
    image_url: str
    category: str
    article: str = None  
    stock: int = 0  

class UserRoleUpdate(BaseModel):
    role: str

# --- API ---

@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.login == user.login).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Пользователь уже существует")
    
    role = "user"
    if user.login == "admin":
        role = "admin"
        
    new_user = models.User(login=user.login, password=user.password, role=role)
    db.add(new_user)
    db.commit()
    return {"message": "Регистрация успешна"}

@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.login == user.login).first()
    if not db_user or db_user.password != user.password:
        raise HTTPException(status_code=400, detail="Неверный логин или пароль")
    
    log_entry = models.Log(user_login=db_user.login, action="Вход в систему")
    db.add(log_entry)
    db.commit()
    
    return {"login": db_user.login, "role": db_user.role}

@app.post("/logs")
def create_log(log: LogCreate, db: Session = Depends(get_db)):
    new_log = models.Log(user_login=log.user_login, action=log.action)
    db.add(new_log)
    db.commit()
    return {"status": "ok"}

@app.get("/logs")
def get_logs(db: Session = Depends(get_db)):
    return db.query(models.Log).order_by(models.Log.timestamp.desc()).all()

@app.post("/import-products")
async def import_products(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Читаем содержимое
    content = await file.read()
    
    # Проверяем, что это CSV
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="На бесплатном Vercel поддерживаются только .csv файлы (Excel сохраните как CSV)")

    try:
        # Декодируем байты в текст
        decoded = content.decode('utf-8').splitlines()
        reader = csv.DictReader(decoded)
        
        count = 0
        for row in reader:
            # Убираем лишние пробелы из названий колонок
            row = {k.strip(): v for k, v in row.items()}
            
            if not row.get('name') or not row.get('price'):
                continue

            art = row.get('article', '')
            existing = None
            if art:
                existing = db.query(models.Product).filter(models.Product.article == art).first()

            if existing:
                existing.price = int(row['price'])
                existing.stock = int(row.get('stock', 0))
            else:
                new_p = models.Product(
                    name=row['name'],
                    brand=row.get('brand', 'Unknown'),
                    price=int(row['price']),
                    category=row.get('category', 'other'),
                    article=art if art else None,
                    stock=int(row.get('stock', 0)),
                    image_url=row.get('image_url', "assets/images/no-image.webp")
                )
                db.add(new_p)
            count += 1
        
        db.commit()
        return {"status": "success", "message": f"Обработано товаров: {count}"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка обработки: {str(e)}")

@app.get("/products")
def get_products(q: str = None, db: Session = Depends(get_db)):
    query = db.query(models.Product)
    print(f"🔎 ПОИСКОВЫЙ ЗАПРОС: '{q}'")
    if q:
        # Поиск по названию ИЛИ бренду
        query = query.filter(
            (models.Product.name.ilike(f"%{q}%")) | 
            (models.Product.brand.ilike(f"%{q}%"))
        )
        
    return query.all()

@app.get("/products/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return product

@app.post("/products")
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    new_product = models.Product(
        name=product.name, 
        brand=product.brand, 
        price=product.price,
        image_url=product.image_url,
        category=product.category
    )
    db.add(new_product)
    db.commit()
    return {"status": "created"}

@app.put("/products/{product_id}")
def update_product(product_id: int, product: ProductCreate, db: Session = Depends(get_db)):
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    
    if not db_product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    
    # Обновляем поля
    db_product.name = product.name
    db_product.brand = product.brand
    db_product.price = product.price
    db_product.image_url = product.image_url
    db_product.category = product.category
    
    db.commit()
    return {"status": "updated", "name": db_product.name}

@app.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    
    db.delete(db_product)
    db.commit()
    return {"status": "deleted"}

# --- ПОЛЬЗОВАТЕЛИ ---

@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    return [{"id": u.id, "login": u.login, "role": u.role} for u in users]

@app.put("/users/{user_id}/role")
def update_user_role(user_id: int, role_data: UserRoleUpdate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    user.role = role_data.role
    db.commit()
    
    return {"status": "success", "new_role": user.role}

# --- STATIC FILES (В самом конце!) ---
current_dir = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.join(current_dir, "frontend")

app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")