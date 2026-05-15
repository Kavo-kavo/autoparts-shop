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
from sqlalchemy import func

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

class ProfileUpdate(BaseModel):
    phone: str
    email: str = None
    car_info: str = None
    vin_code: str = None

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

class CartItem(BaseModel):
    id: int
    quantity: int = 1

class OrderRequest(BaseModel):
    username: str
    items: List[CartItem]
    phone: str
    email: str
    address: str


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

@app.put("/api/update-profile/{username}")
def update_profile(username: str, data: ProfileUpdate, db: Session = Depends(get_db)):
    # Ищем клиента, связанного с этим логином
    customer = db.query(models.Customer).filter(models.Customer.full_name == username).first()
    
    if not customer:
        # Если записи в таблице Customer еще нет — создаем её
        customer = models.Customer(full_name=username)
        db.add(customer)
    
    # Обновляем поля
    customer.phone = data.phone
    customer.email = data.email
    customer.car_info = data.car_info
    customer.vin_code = data.vin_code
    
    db.commit()
    return {"status": "success", "message": "Профиль обновлен"}

@app.get("/api/orders/{order_id}/items")
def get_order_items(order_id: int, db: Session = Depends(get_db)):
    # Ищем все позиции в заказе и соединяем с таблицей товаров
    items = db.query(models.OrderItem).filter(models.OrderItem.order_id == order_id).all()
    
    result = []
    for item in items:
        # Ищем информацию о товаре для каждой позиции
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        result.append({
            "name": product.name if product else "Товар удален",
            "brand": product.brand if product else "-",
            "quantity": item.quantity,
            "price": item.price_at_purchase
        })
    return result

@app.get("/api/admin/stats")
def get_admin_stats(db: Session = Depends(get_db)):
    total_revenue = db.query(func.sum(models.Order.total_price)).filter(models.Order.status == "Доставлен").scalar() or 0
    
    new_orders_count = db.query(models.Order).filter(models.Order.status == "Новый").count()
    
    low_stock_count = db.query(models.Product).filter(models.Product.stock <= models.Product.min_stock).count()

    sales_by_day = db.query(
        func.to_char(models.Order.created_at, 'DD.MM').label('date'),
        func.sum(models.Order.total_price).label('sum')
    ).group_by('date').order_by('date').limit(7).all()

    top_products = db.query(
        models.Product.name,
        func.sum(models.OrderItem.quantity).label('total_qty')
    ).join(models.OrderItem).group_by(models.Product.name).order_by(func.sum(models.OrderItem.quantity).desc()).limit(5).all()

    return {
        "revenue": total_revenue,
        "new_orders": new_orders_count,
        "low_stock": low_stock_count,
        "sales_chart": [{"date": s[0], "sum": s[1]} for s in sales_by_day],
        "top_products": [{"name": p[0], "qty": p[1]} for p in top_products]
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

class OrderStatusUpdate(BaseModel):
    status: str

@app.get("/api/admin/orders")
def get_all_orders_admin(db: Session = Depends(get_db)):
    orders = db.query(models.Order).order_by(models.Order.created_at.desc()).all()
    
    result = []
    for o in orders:
        customer = db.query(models.Customer).filter(models.Customer.id == o.customer_id).first()
        result.append({
            "id": o.id,
            "customer_name": customer.full_name if customer else "Удален",
            "customer_phone": customer.phone if customer else "-",
            "total_price": o.total_price,
            "status": o.status,
            "date": o.created_at.strftime("%d.%m.%Y %H:%M")
        })
    return result

@app.put("/api/admin/orders/{order_id}/status")
def update_order_status(order_id: int, data: OrderStatusUpdate, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    
    old_status = order.status
    order.status = data.status
    
    # Автоматически пишем в логи (у тебя это реализовано)
    log_entry = models.Log(user_login="admin", action=f"Смена статуса заказа №{order_id}: {old_status} -> {data.status}")
    db.add(log_entry)
    
    db.commit()
    return {"message": "Статус обновлен"}

@app.post("/api/orders")
def create_order(order_data: OrderRequest, db: Session = Depends(get_db)):
    try:
        # 1. Проверяем пользователя
        user = db.query(models.User).filter(models.User.login == order_data.username).first()
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        # 2. Ищем или создаем Клиента
        customer = db.query(models.Customer).filter(models.Customer.full_name == user.login).first()
        if not customer:
            # Важно: добавляем все обязательные поля
            customer = models.Customer(full_name=user.login, phone="Не указан", email="")
            db.add(customer)
            db.flush() 

        # 3. Создаем Заказ
        new_order = models.Order(
            customer_id=customer.id,
            status="Новый",
            total_price=0.0
        )
        db.add(new_order)
        db.flush()

        total_sum = 0
        # 4. Добавляем товары
        for cart_item in order_data.items:
            product = db.query(models.Product).filter(models.Product.id == int(cart_item.id)).first()
            if not product:
                continue
            
            total_sum += product.price * cart_item.quantity

            # Проверяем склад
            if product.stock and product.stock >= cart_item.quantity:
                product.stock -= cart_item.quantity
            
            order_item = models.OrderItem(
                order_id=new_order.id,
                product_id=product.id,
                quantity=cart_item.quantity,
                price_at_purchase=product.price
            )
            db.add(order_item)

        new_order.total_price = total_sum
        db.commit()
        return {"status": "success", "order_id": new_order.id}

    except Exception as e:
        db.rollback()
        print(f"ERROR: {str(e)}") # Это появится в логах Vercel
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")

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
