import os
import sys
import time
from sqlalchemy import create_engine

# 1. Импортируем Base
from app.db.session import Base

# 2. ВАЖНО!!! Импортируем сами модели, чтобы они зарегистрировались в Base
# Проверьте, где именно лежат ваши модели User, Food, Restaurant.
# Обычно это app.models (если там __init__.py) или app.models.user
try:
    # Попытка 1: Если все в app/models.py или app/models/__init__.py
    from app.models import User
    print("✅ Модель User найдена в app.models")
except ImportError:
    try:
        # Попытка 2: Если модели разбросаны по файлам (app/models/user.py)
        from app.models.user import User
        # Добавьте сюда другие модели, если нужно (например, Food)
        # from app.models.food import Food
        print("✅ Модель User найдена в app.models.user")
    except ImportError as e:
        print(f"❌ ОШИБКА: Не удалось найти модель User. Проверьте пути импорта! {e}")
        # Мы не выходим, пробуем создать что есть, но скорее всего это ошибка.

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    print("❌ Ошибка: DATABASE_URL не найден")
    sys.exit(1)

def init_db():
    engine = create_engine(DATABASE_URL)
    
    print("🔄 Подключение к базе данных...")
    
    # 3. Создаем таблицы
    # Теперь, когда User импортирован, Base знает о нем!
    print("🔨 Попытка создать таблицы...")
    Base.metadata.create_all(bind=engine)
    
    print("✅ Таблицы (надеюсь) созданы!")

if __name__ == "__main__":
    init_db()