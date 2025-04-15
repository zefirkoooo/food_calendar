import pandas as pd
from typing import Dict, List, Tuple
from .models import Dish, DayMenu

# Константы для маппинга
DAY_MAPPING: Dict[str, str] = {
    'Понедельник': 'monday',
    'понедельник': 'monday',
    'Вторник': 'tuesday',
    'вторник': 'tuesday',
    'Среда': 'wednesday',
    'среда': 'wednesday',
    'Четверг': 'thursday',
    'четверг': 'thursday',
    'Пятница': 'friday',
    'пятница': 'friday',
    'пятниица': 'friday',  
    'ПЯТНИЦА': 'friday'
}

CATEGORY_MAPPING: Dict[str, str] = {
    'САЛАТЫ': 'salad',
    'Салаты': 'salad',
    'салаты': 'salad',
    'СУПЫ': 'soup',
    'Супы': 'soup',
    'супы': 'soup',
    'ГОРЯЧЕЕ': 'main',
    'Горячее': 'main',
    'горячее': 'main',
    'ГАРНИРЫ': 'side',
    'Гарниры': 'side',
    'гарниры': 'side',
    'ВЫПЕЧКА': 'bakery',
    'Выпечка': 'bakery',
    'выпечка': 'bakery'
}

def parse_dish_text(dish_text: str) -> Tuple[str, str]:
    """
    Извлекает название блюда и описание из текста.
    
    Args:
        dish_text: Текст с информацией о блюде
        
    Returns:
        Tuple[str, str]: (название блюда, описание)
    """
    dish_name = dish_text
    description = ""
    
    start_idx = dish_text.find('(')
    end_idx = dish_text.rfind(')')
    
    if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
        dish_name = dish_text[:start_idx].strip()
        description = dish_text[start_idx:end_idx + 1].strip()[1:-1].strip()
    
    return dish_name, description

def is_fasting_dish(dish_text: str) -> bool:
    """
    Проверяет, является ли блюдо постным.
    
    Args:
        dish_text: Текст с информацией о блюде
        
    Returns:
        bool: True если блюдо постное, иначе False
    """
    return any(word in dish_text.lower() for word in ['постн', 'пост'])

def parse_excel_menu(file_path: str) -> int:
    """
    Парсит Excel файл с блюдами и добавляет их в базу данных.
    Структура: дни недели в колонках, категории блюд в строках.
    
    Args:
        file_path: Путь к Excel файлу
        
    Returns:
        int: Количество добавленных блюд
        
    Raises:
        Exception: При ошибке парсинга файла
    """
    try:
        df = pd.read_excel(file_path, header=0, keep_default_na=False)
        print("Columns in Excel:", df.columns.tolist())
        
        # Создаем дни недели
        for day_code in set(DAY_MAPPING.values()):
            DayMenu.objects.get_or_create(day=day_code)

        # Очищаем старые связи
        for day_menu in DayMenu.objects.all():
            day_menu.available_dishes.clear()

        count = 0
        current_category = None

        for index, row in df.iterrows():
            category_cell = str(row.iloc[0]).strip()
            if category_cell and any(cat.lower() in category_cell.lower() for cat in CATEGORY_MAPPING.keys()):
                current_category = next(
                    (cat_code for cat_name, cat_code in CATEGORY_MAPPING.items() 
                     if cat_name.lower() in category_cell.lower()),
                    None
                )
                if current_category:
                    print(f"Found category: {category_cell} -> {current_category}")

            if current_category:
                for col in df.columns[1:]:
                    normalized_col = col.strip().lower()
                    day_code = next(
                        (code for day_name, code in DAY_MAPPING.items() 
                         if day_name.lower() in normalized_col),
                        None
                    )
                    
                    if day_code:
                        cell_content = str(row[col]).strip()
                        
                        if cell_content and cell_content != 'nan':
                            dishes = [d.strip() for d in cell_content.split('\n') if d.strip()]
                            
                            for dish_text in dishes:
                                dish_name, description = parse_dish_text(dish_text)
                                
                                if dish_name:
                                    print(f"Creating dish: {dish_name} ({current_category})")
                                    
                                    dish, created = Dish.objects.get_or_create(
                                        name=dish_name,
                                        defaults={
                                            'description': description,
                                            'category': current_category,
                                            'is_fasting': is_fasting_dish(dish_text)
                                        }
                                    )

                                    if not created:
                                        dish.category = current_category
                                        dish.is_fasting = is_fasting_dish(dish_text)
                                        if description:
                                            dish.description = description
                                        dish.save()

                                    day_menu = DayMenu.objects.get(day=day_code)
                                    day_menu.available_dishes.add(dish)
                                    count += 1
                                    print(f"Added dish {dish_name} to {normalized_col}")

        return count
    except Exception as e:
        print(f"Error parsing Excel file: {str(e)}")
        raise