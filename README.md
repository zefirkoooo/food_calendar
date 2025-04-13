# Food Calendar

A Django-based web application for managing weekly meal plans and dish selections.

Веб-приложение на основе Django для управления еженедельными планами питания и выборами блюд.

## Features EN

- Weekly meal calendar
- Dish selection for each day
- User management system
- Excel file import/export
- Mobile-friendly interface
  
## Особенности RU
- Календарь питания на неделю
- Выбор блюд на каждый день
- Система управления пользователями
- Импорт/экспорт файлов Excel
- Удобный интерфейс для мобильных устройств

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/food_calendar.git
cd food_calendar
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Apply migrations:
```bash
python manage.py migrate
```

5. Create superuser:
```bash
python manage.py createsuperuser
```

6. Run development server:
```bash
python manage.py runserver
```

## Project Structure

```
food_calendar/
├── meal_planner/          # Main application
│   ├── migrations/        # Database migrations
│   ├── static/           # Static files
│   ├── templates/        # HTML templates
│   ├── forms.py          # Django forms
│   ├── models.py         # Database models
│   ├── urls.py           # URL patterns
│   └── views.py          # View functions
├── food_calendar/        # Project settings
├── manage.py            # Django management script
└── requirements.txt     # Python dependencies
```
