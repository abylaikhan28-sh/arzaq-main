import os
import sys
from sqlalchemy import create_engine
from app.db.session import Base  # Импорт из вашего session.py
from app.models import * # Импортируем все модели, чтобы Base о них узнал

# Получаем адрес базы данных от Render
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    print("❌ Ошибка: Не найден DATABASE_URL")
    sys.exit(1)

def init_db():
    try:
        # Создаем движок
        engine = create_engine(DATABASE_URL)
        print("🔄 Подключение к базе данных...")
        
        # Самая главная команда: СОЗДАТЬ ВСЕ ТАБЛИЦЫ
        print("🔨 Создание таблиц (users, foods и др)...")
        Base.metadata.create_all(bind=engine)
        
        print("✅ Успех! Таблицы созданы.")
    except Exception as e:
        print(f"❌ Ошибка при создании таблиц: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_db()