import pandas as pd
from .models import Dish, DayMenu

def parse_excel_menu(file_path):
    """
    Парсит Excel файл с блюдами и добавляет их в базу данных.
    """
    try:
        df = pd.read_excel(file_path)

        required_columns = ['День недели', 'Блюдо']
        if not all(col in df.columns for col in required_columns):
            return 0

        day_mapping = {
            'Понедельник': 'monday',
            'Вторник': 'tuesday',
            'Среда': 'wednesday',
            'Четверг': 'thursday',
            'Пятница': 'friday'
        }

        # Создаем дни недели, если их нет
        for day_name, day_code in day_mapping.items():
            DayMenu.objects.get_or_create(day=day_code)

        # Очищаем старые связи между блюдами и днями
        for day_menu in DayMenu.objects.all():
            day_menu.available_dishes.clear()

        # Добавляем новые блюда и связи
        count = 0
        for _, row in df.iterrows():
            day_name = row['День недели']
            dish_name = row['Блюдо']
            description = row.get('Описание', '')  # Необязательное поле

            if day_name in day_mapping:
                # Создаем или получаем блюдо
                dish, created = Dish.objects.get_or_create(
                    name=dish_name,
                    defaults={'description': description}
                )

                # Получаем день недели
                day_menu = DayMenu.objects.get(day=day_mapping[day_name])

                # Добавляем блюдо в доступные для этого дня
                day_menu.available_dishes.add(dish)
                count += 1

        return count
    except Exception as e:
        raise Exception(f"Ошибка при обработке Excel файла: {str(e)}")