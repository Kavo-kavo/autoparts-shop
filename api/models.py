from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    login = Column(String, unique=True, index=True)
    password = Column(String) 
    role = Column(String, default="user") 

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    phone = Column(String, unique=True, index=True)
    email = Column(String, nullable=True)
    car_info = Column(String, nullable=True) 
    vin_code = Column(String, nullable=True) 
    
    orders = relationship("Order", back_populates="customer")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    brand = Column(String)
    price = Column(Integer)
    image_url = Column(String)
    category = Column(String)
    
    #ПОЛЯ ДЛЯ CRM:
    article = Column(String, unique=True, index=True) # Артикул запчасти
    stock = Column(Integer, default=0)              # Текущий остаток на складе
    min_stock = Column(Integer, default=5)          # Порог для уведомления 

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    status = Column(String, default="Новый") # Новый, В обработке, Оплачен, Доставлен, Отменен
    total_price = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")

#  Состав заказа (детализация)
class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, default=1)
    price_at_purchase = Column(Integer) # Цена на момент покупки (может измениться в каталоге)
    
    order = relationship("Order", back_populates="items")
    product = relationship("Product")

#  Логи 
class Log(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, index=True)
    user_login = Column(String)
    action = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class CrossReference(Base):
    __tablename__ = "cross_references"
    id = Column(Integer, primary_key=True, index=True)
    # Артикул запчасти А
    article_1 = Column(String, index=True)
    # Артикул запчасти Б (которая является аналогом)
    article_2 = Column(String, index=True)
