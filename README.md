# Radium Food Project / Проект Radium Food

[English](#english) | [Русский](#russian)

<a name="english"></a>
# English

## Description
Radium Food is a Django-based web application for food service management. The project includes features for calendar management, user authentication, and various administrative tools.

## Prerequisites
- Python 3.8 or higher
- PostgreSQL
- Redis
- Node.js (for frontend development)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd radium_food
```

2. Create and activate a virtual environment:
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the root directory with the following variables:
```
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=postgres://user:password@localhost:5432/dbname
REDIS_URL=redis://localhost:6379/0
```

5. Run database migrations:
```bash
python manage.py migrate
```

6. Create a superuser:
```bash
python manage.py createsuperuser
```

7. Start the development server:
```bash
python manage.py runserver
```

## Running with Celery
1. Start Redis server
2. Start Celery worker:
```bash
celery -A radium_food worker -l info
```
3. Start Celery beat:
```bash
celery -A radium_food beat -l info
```

## Project Structure
- `calendar_app/` - Calendar management application
- `radium_food/` - Main project configuration
- `templates/` - HTML templates
- `media/` - User-uploaded files
- `excel_files/` - Excel file processing
- `logs/` - Application logs

## Features
- User authentication and authorization
- Calendar management
- Excel file processing
- Admin dashboard
- API endpoints
- Task scheduling with Celery
- File upload and management

## Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License
This project is licensed under the terms of the license included in the repository.

---

<a name="russian"></a>
# Русский

## Описание
Radium Food - это веб-приложение на базе Django для управления услугами общественного питания. Проект включает функции управления календарем, аутентификации пользователей и различные административные инструменты.

## Требования
- Python 3.8 или выше
- PostgreSQL
- Redis
- Node.js (для фронтенд-разработки)

## Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd radium_food
```

2. Создайте и активируйте виртуальное окружение:
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Настройте переменные окружения:
Создайте файл `.env` в корневой директории со следующими переменными:
```
DEBUG=True
SECRET_KEY=ваш-секретный-ключ
DATABASE_URL=postgres://пользователь:пароль@localhost:5432/имя_бд
REDIS_URL=redis://localhost:6379/0
```

5. Выполните миграции базы данных:
```bash
python manage.py migrate
```

6. Создайте суперпользователя:
```bash
python manage.py createsuperuser
```

7. Запустите сервер разработки:
```bash
python manage.py runserver
```

## Запуск с Celery
1. Запустите сервер Redis
2. Запустите Celery worker:
```bash
celery -A radium_food worker -l info
```
3. Запустите Celery beat:
```bash
celery -A radium_food beat -l info
```

## Структура проекта
- `calendar_app/` - Приложение управления календарем
- `radium_food/` - Основная конфигурация проекта
- `templates/` - HTML шаблоны
- `media/` - Загруженные пользователями файлы
- `excel_files/` - Обработка Excel файлов
- `logs/` - Логи приложения

## Функциональность
- Аутентификация и авторизация пользователей
- Управление календарем
- Обработка Excel файлов
- Административная панель
- API endpoints
- Планирование задач с Celery
- Загрузка и управление файлами

## Участие в разработке
1. Форкните репозиторий
2. Создайте ветку для новой функции
3. Внесите изменения
4. Отправьте изменения в ветку
5. Создайте Pull Request

## Лицензия
Этот проект распространяется под лицензией, включенной в репозиторий. 