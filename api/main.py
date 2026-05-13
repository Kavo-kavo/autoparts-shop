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
    content = await file.read()
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Пожалуйста, используйте формат .csv")

    # --- 1. РЕШАЕМ ПРОБЛЕМУ С КОДИРОВКОЙ ---
    try:
        # Сначала пробуем стандартный UTF-8
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        try:
            # Если не вышло (ошибка 0xeb) — значит это Windows-1251 (Excel)
            text = content.decode('cp1251')
        except Exception:
            raise HTTPException(status_code=400, detail="Не удалось определить кодировку файла. Используйте UTF-8 или Windows-1251.")

    try:
        text = text.strip()
        f = io.StringIO(text)

        first_line = text.split('\n')[0]
        if ';' in first_line:
            sep = ';'
        else:
            sep = ','

        reader = csv.DictReader(f, delimiter=sep)
        
        reader.fieldnames = [field.strip().lower() for field in reader.fieldnames]
        
        count = 0
        skipped = 0
        
        for row in reader:
            # Убираем пробелы из значений
            row = {k: (v.strip() if v else v) for k, v in row.items()}

            name = row.get('name')
            price_raw = row.get('price')

            if not name or not price_raw:
                skipped += 1
                continue

            # В русском Excel цена может быть "500,50" (с запятой)
            # Заменяем запятую на точку, чтобы Python смог превратить это в число
            price_str = str(price_raw).replace(',', '.')
            try:
                price = int(float(price_str))
            except:
                skipped += 1
                continue

            art = row.get('article', '')
            existing = None
            if art:
                existing = db.query(models.Product).filter(models.Product.article == art).first()

            if existing:
                existing.price = price
                stock_raw = row.get('stock', '0').replace(',', '.')
                existing.stock = int(float(stock_raw))
            else:
                stock_raw = row.get('stock', '0').replace(',', '.')
                new_p = models.Product(
                    name=name,
                    brand=row.get('brand', 'Unknown'),
                    price=price,
                    category=row.get('category', 'other'),
                    article=art if art else None,
                    stock=int(float(stock_raw)),
                    image_url=row.get('image_url', "assets/images/no-image.webp")
                )
                db.add(new_p)

            crosses_raw = row.get('oem_cross', '')
            if art and crosses_raw:
                # Разделяем строку по ";" (например, "W712; 03C115561H" -> ["W712", "03C115561H"])
                cross_list = [c.strip() for c in crosses_raw.split(';') if c.strip()]
                
                for cross_art in cross_list:
                    # Проверяем, нет ли уже такой связки в базе
                    # (ищем в обе стороны, чтобы не дублировать)
                    exists = db.query(models.CrossReference).filter(
                        ((models.CrossReference.article_1 == art) & (models.CrossReference.article_2 == cross_art)) |
                        ((models.CrossReference.article_1 == cross_art) & (models.CrossReference.article_2 == art))
                    ).first()
                    
                    if not exists:
                        new_cross = models.CrossReference(
                            article_1=art, 
                            article_2=cross_art
                        )
                        db.add(new_cross)
            count += 1
        
        db.commit()
        
        if count == 0:
            return {
                "status": "warning", 
                "message": f"Товары не найдены. Проверьте заголовки. Мы увидели: {', '.join(reader.fieldnames)}"
            }

        return {"status": "success", "message": f"Успешно добавлено/обновлено: {count}"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Ошибка обработки данных: {str(e)}")

@app.get("/api/my-profile/{username}")
def get_user_profile(username: str, db: Session = Depends(get_db)):
    # 1. Ищем пользователя
    user = db.query(models.User).filter(models.User.login == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # 2. Ищем данные клиента (авто, телефон и т.д.), связанные с этим логином
    # Для простоты ищем по совпадению full_name или создадим связь, если её нет
    customer = db.query(models.Customer).filter(models.Customer.full_name == username).first()
    
    # 3. Ищем все заказы этого пользователя
    orders = []
    total_spent = 0
    if customer:
        orders = db.query(models.Order).filter(models.Order.customer_id == customer.id).all()
        total_spent = sum(order.total_price for order in orders)

    return {
        "login": user.login,
        "role": user.role,
        "car_info": customer.car_info if customer else "Не указано",
        "vin_code": customer.vin_code if customer else "Не указано",
        "stats": {
            "total_orders": len(orders),
            "total_spent": total_spent,
        },
        "orders": [
            {
                "id": o.id,
                "status": o.status,
                "total_price": o.total_price,
                "date": o.created_at.strftime("%d.%m.%Y")
            } for o in orders
        ]
    }

@app.get("/products")
def get_products(q: str = None, db: Session = Depends(get_db)):
    if not q:
        products = db.query(models.Product).all()
        # По умолчанию это не аналоги
        for p in products:
            setattr(p, "is_analog", False)
        return products

    q_clean = q.strip().lower()
    
    # 1. Ищем прямые совпадения по артикулу (Оригинал)
    originals = db.query(models.Product).filter(models.Product.article.ilike(q_clean)).all()
    original_ids = {p.id for p in originals}
    for p in originals:
        setattr(p, "is_analog", False)

    # 2. Ищем аналоги через кросс-номера
    cross_entries = db.query(models.CrossReference).filter(
        (models.CrossReference.article_1.ilike(q_clean)) | 
        (models.CrossReference.article_2.ilike(q_clean))
    ).all()

    cross_articles = set()
    for entry in cross_entries:
        if entry.article_1.lower() != q_clean: cross_articles.add(entry.article_1)
        if entry.article_2.lower() != q_clean: cross_articles.add(entry.article_2)

    analogs = db.query(models.Product).filter(models.Product.article.in_(cross_articles)).all()
    # Оставляем только те, что не попали в список оригиналов
    final_analogs = []
    for p in analogs:
        if p.id not in original_ids:
            setattr(p, "is_analog", True)
            final_analogs.append(p)
            original_ids.add(p.id) # Чтобы не дублировать в поиске по названию

    # 3. Ищем по названию и бренду (Обычный поиск)
    others = db.query(models.Product).filter(
        (models.Product.name.ilike(f"%{q_clean}%")) | 
        (models.Product.brand.ilike(f"%{q_clean}%"))
    ).all()
    
    final_others = []
    for p in others:
        if p.id not in original_ids:
            setattr(p, "is_analog", False)
            final_others.append(p)

    # Возвращаем в строгом порядке: Оригиналы -> По названию -> Аналоги
    return originals + final_others + final_analogs

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
frontend_dir = os.path.join(current_dir, "..", "frontend")

app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
