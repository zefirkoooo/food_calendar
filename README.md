# Food Calendar

Веб-приложение для планирования и управления меню питания на неделю.

## Возможности
- Загрузка и парсинг Excel-меню
- Выбор блюд пользователями
- Управление пользователями и ролями
- Экспорт и анализ данных
- Адаптивный дизайн для мобильных устройств

## Установка
1. Клонируйте репозиторий:
   ```
   git clone https://github.com/zefirkoooo/food_calendar.git
   cd food_calendar
   ```
2. Создайте и активируйте виртуальное окружение:
   ```
   python -m venv .venv
   source .venv/bin/activate  # или .venv\Scripts\activate для Windows
   ```
3. Установите зависимости:
   ```
   pip install -r requirements.txt
   ```
4. Примените миграции:
   ```
   python manage.py migrate
   ```
5. Запустите сервер:
   ```
   python manage.py runserver
   ```
   
## Интерфейс

<p align="center">
  <img src="https://github.com/user-attachments/assets/a11963cf-c884-43eb-8aa4-8bf71ae47361" alt="image" />
</p>

## Лицензия
Смотреть файл LICENSE 
