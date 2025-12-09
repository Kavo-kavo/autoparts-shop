import requests
import json

# Адрес твоего сервера (он должен быть запущен!)
API_URL = "http://127.0.0.1:8000/products"

# Список товаров для добавления
products = [
    {
        "name": "Моторное масло Mobil 1 FS 0W-40 (4л)",
        "brand": "Mobil",
        "price": 5200,
        "category": "oil",
        "image_url": "assets/images/oil_mobil.webp"
    },
    {
        "name": "Тормозные колодки передние",
        "brand": "Brembo",
        "price": 3800,
        "category": "brakes",
        "image_url": "assets/images/pads_brembo.webp"
    },
    {
        "name": "Тормозной диск вентилируемый",
        "brand": "Bosch",
        "price": 4100,
        "category": "brakes",
        "image_url": "assets/images/disk_bosch.webp"
    },
    {
        "name": "Фильтр масляный",
        "brand": "Mann-Filter",
        "price": 850,
        "category": "filters",
        "image_url": "assets/images/filter_mann.webp"
    },
    {
        "name": "Фильтр воздушный",
        "brand": "Filtron",
        "price": 600,
        "category": "filters",
        "image_url": "assets/images/filter_air.webp"
    },
    {
        "name": "Свеча зажигания Iridium",
        "brand": "NGK",
        "price": 1200,
        "category": "engine",
        "image_url": "assets/images/spark_ngk.webp"
    },
    {
        "name": "Ремень ГРМ",
        "brand": "Contitech",
        "price": 2500,
        "category": "engine",
        "image_url": "assets/images/belt.webp"
    }
]

print(f"Начинаю добавление {len(products)} товаров...")

for p in products:
    try:
        # Отправляем POST запрос на твой сервер
        response = requests.post(API_URL, json=p)
        
        if response.status_code == 200:
            print(f"[OK] Добавлен: {p['name']}")
        else:
            print(f"[ERROR] Не удалось добавить {p['name']}: {response.text}")
            
    except Exception as e:
        print(f"[FAIL] Ошибка соединения: {e}")

print("Готово!")