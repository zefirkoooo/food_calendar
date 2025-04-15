import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Count
import pandas as pd
from io import BytesIO
from .models import Dish, DayMenu, DishSelection, UserSelection
from .forms import ExcelUploadForm, UserSelectionForm, DishSelectionForm, SimpleUserCreationForm, AdminPasswordForm, ChangePasswordForm, SaveSelectionForm
from .utils import parse_excel_menu
import xlsxwriter
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.db.models import Prefetch
import json
import csv
import io
import datetime
import traceback
from django.contrib.auth.hashers import make_password
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

# Константа для времени жизни кэша
CACHE_TTL = 60 * 15  # 15 минут

def is_admin(user):
    """Проверка, является ли пользователь администратором"""
    return user.is_superuser


@login_required
@user_passes_test(is_admin)
def manage_users(request):
    """Страница управления пользователями"""
    if request.method == 'POST':
        form = SimpleUserCreationForm(request.POST)
        if form.is_valid():
            try:
                # Создаем пользователя с паролем
                user = form.save()
                messages.success(request, f'Пользователь {user.username} успешно создан')
            except Exception as e:
                messages.error(request, f'Произошла ошибка при создании пользователя: {str(e)}')
            return redirect('meal_planner:manage_users')
    else:
        form = SimpleUserCreationForm()
    
    users = User.objects.all()
    return render(request, 'meal_planner/manage_users.html', {
        'form': form,
        'users': users
    })


@login_required
@user_passes_test(is_admin)
def export_selections(request, format='excel'):
    """Экспорт выборок пользователей"""
    # Получаем все выборки
    selections = DishSelection.objects.filter(selected=True).select_related('user', 'day_menu', 'dish')
    
    if format == 'excel':
        # Создаем DataFrame
        data = []
        for selection in selections:
            data.append({
                'Пользователь': selection.user.username,
                'День недели': selection.day_menu.get_day_display(),
                'Блюдо': selection.dish.name,
                'Описание блюда': selection.dish.description or '',
            })
        
        df = pd.DataFrame(data)
        
        # Создаем Excel файл в памяти
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Выборки')
        
        # Возвращаем файл
        output.seek(0)
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=selections.xlsx'
        return response
    
    elif format == 'sql':
        # Генерируем SQL запрос
        sql = []
        for selection in selections:
            sql.append(f"INSERT INTO meal_planner_dishselection (user_id, day_menu_id, dish_id, selected) "
                      f"VALUES ({selection.user.id}, {selection.day_menu.id}, {selection.dish.id}, 1);")
        
        response = HttpResponse('\n'.join(sql), content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename=selections.sql'
        return response


def login_view(request):
    """Страница входа в систему"""
    if request.user.is_authenticated:
        return redirect('meal_planner:index')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, 'Вход в систему', extra_tags='shown')
            if user.username == 'root':
                return redirect('meal_planner:index')
            else:
                request.session['selected_user_id'] = user.id
                return redirect('meal_planner:index')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль')
    
    return render(request, 'meal_planner/login.html')


def logout_view(request):
    """Выход пользователя из системы"""
    logout(request)
    messages.success(request, 'Вы успешно вышли из системы', extra_tags='shown')
    return redirect('meal_planner:index')


@login_required
def calendar_view(request):
    cache_key = f'calendar_view_{request.user.id}'
    cached_data = cache.get(cache_key)

    if cached_data is None:
        print("[VIEW calendar_view] Кэш не найден, запрашиваем данные...")
        # Оптимизируем запросы с помощью select_related и prefetch_related
        days_qs = (DayMenu.objects
                  .all()
                  .order_by('id')
                  .prefetch_related(
                      Prefetch('dishselection_set', 
                              queryset=DishSelection.objects
                              .filter(user=request.user)
                              .select_related('dish'), 
                              to_attr='user_dish_selections'),
                      'available_dishes'
                  ))

        days_list = list(days_qs)

        # Группируем выбранные пользователем блюда по дням и категориям
        selected_dishes_by_day = {}
        categories = set()
        
        for day in days_list:
            dishes_by_category = {}
            for sel in day.user_dish_selections:
                category = sel.dish.category
                categories.add(category)
                dishes_by_category.setdefault(category, []).append(sel.dish)
            
            selected_dishes_by_day[day.id] = dishes_by_category
            print(f"[VIEW calendar_view] День {day.get_day_display()} (ID:{day.id}): "
                  f"Доступно блюд - {len(day.available_dishes.all())}, "
                  f"Выбрано пользователем - {sum(len(dishes) for dishes in dishes_by_category.values())}")

        days_for_context = days_list
        selected_dishes_for_context = selected_dishes_by_day
        categories_list = sorted(list(categories))

        cache.set(cache_key, {
            'days': days_for_context,
            'selected_dishes': selected_dishes_for_context,
            'categories': categories_list
        }, CACHE_TTL)
        print("[VIEW calendar_view] Данные закэшированы")

    else:
        print("[VIEW calendar_view] Данные найдены в кэше, восстанавливаем...")
        days_for_context = cached_data['days']
        selected_dishes_for_context = cached_data['selected_dishes']
        categories_list = cached_data.get('categories', [])

    context = {
        'days': days_for_context,
        'selected_dishes': selected_dishes_for_context,
        'categories': categories_list,
        'upload_form': ExcelUploadForm(),
        'selected_user': request.user
    }

    return render(request, 'meal_planner/calendar.html', context)


@login_required
def day_meals_view(request, day_id):
    cache_key = f'day_meals_{day_id}_{request.user.id}'
    cached_data = cache.get(cache_key)

    if cached_data is None:
        print("[VIEW day_meals_view] Кэш не найден, запрашиваем данные...")
        day = get_object_or_404(DayMenu, pk=day_id)
        
        # Получаем все доступные блюда для этого дня
        available_dishes = day.available_dishes.all()
        print(f"[VIEW day_meals_view] Найдено {available_dishes.count()} доступных блюд для дня {day.get_day_display()}")
        
        # Получаем выборы пользователя
        user_selections = DishSelection.objects.filter(
            user=request.user,
            day_menu=day
        ).select_related('dish').values_list('dish_id', flat=True)
        print(f"[VIEW day_meals_view] Найдено {len(user_selections)} выбранных блюд пользователем")
        
        # Группируем блюда по категориям
        categories = {
            'salad': {'name': 'Салаты', 'icon': 'leaf', 'dishes': []},
            'soup': {'name': 'Супы', 'icon': 'bowl-food', 'dishes': []},
            'main': {'name': 'Горячее', 'icon': 'fire', 'dishes': []},
            'side': {'name': 'Гарниры', 'icon': 'carrot', 'dishes': []},
            'bakery': {'name': 'Выпечка', 'icon': 'bread-slice', 'dishes': []},
            'fasting': {'name': 'Постная еда', 'icon': 'leaf', 'dishes': []}
        }
        
        # Заполняем категории блюдами
        for dish in available_dishes:
            if dish.category in categories:
                categories[dish.category]['dishes'].append({
                    'dish': dish,
                    'selected': dish.id in user_selections
                })
        
        # Удаляем пустые категории
        categories = {k: v for k, v in categories.items() if v['dishes']}
        
        cached_data = {
            'day_menu': day,
            'categories': categories
        }
        
        cache.set(cache_key, cached_data, CACHE_TTL)
        print(f"[VIEW day_meals_view] Данные закэшированы с ключом {cache_key}")
    else:
        print(f"[VIEW day_meals_view] Данные найдены в кэше с ключом {cache_key}")

    context = {
        'day_menu': cached_data['day_menu'],
        'categories': cached_data['categories']
    }

    return render(request, 'meal_planner/day_meals.html', context)


@login_required
def select_dish(request, day_id, dish_id):
    day = get_object_or_404(DayMenu, pk=day_id)
    dish = get_object_or_404(Dish, pk=dish_id)
    
    # Проверяем существование выбора одним запросом
    existing_selection = DishSelection.objects.filter(
        day_menu=day,
        dish=dish,
        user=request.user
    ).first()
    
    if not existing_selection:
        DishSelection.objects.create(
            day_menu=day,
            dish=dish,
            user=request.user
        )
        
        # Очищаем кэш для этого дня
        cache.delete(f'day_meals_{day_id}_{request.user.id}')
        cache.delete(f'calendar_view_{request.user.id}')
    
    return redirect('meal_planner:day_meals', day_id=day_id)


@login_required
def deselect_dish(request, day_id, dish_id):
    day = get_object_or_404(DayMenu, pk=day_id)
    dish = get_object_or_404(Dish, pk=dish_id)
    
    # Удаляем выбор одним запросом
    DishSelection.objects.filter(
        day_menu=day,
        dish=dish,
        user=request.user
    ).delete()
    
    # Очищаем кэш для этого дня
    cache.delete(f'day_meals_{day_id}_{request.user.id}')
    cache.delete(f'calendar_view_{request.user.id}')
    
    return redirect('meal_planner:day_meals', day_id=day_id)


@login_required
@user_passes_test(is_admin)
def upload_excel(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        try:
            excel_file = request.FILES['excel_file']
            print("[PARSE_V3] Начало парсинга Excel файла (новый формат)")

            # Читаем файл, предполагая, что дни недели находятся во второй строке (индекс 1)
            # Первая строка (индекс 0) будет проигнорирована как заголовок дат
            try:
                df = pd.read_excel(
                    excel_file,
                    header=1, # Используем вторую строку как заголовок (дни недели)
                    keep_default_na=False,
                    na_filter=False,
                    engine='openpyxl'
                )
                print(f"[PARSE_V3] Файл успешно прочитан. Размер: {df.shape[0]} строк данных, {df.shape[1]} столбцов.")
                # print("[PARSE_V3] Заголовки (дни недели):")
                # print(df.columns)
                # print("[PARSE_V3] Первые 5 строк данных:")
                # print(df.head().to_string())
            except Exception as e:
                print(f"[PARSE_V3] Ошибка чтения Excel файла: {str(e)}")
                raise ValueError(f"Не удалось прочитать Excel файл. Убедитесь, что вторая строка содержит дни недели. Ошибка: {str(e)}")

            # Очищаем старые данные
            print("[PARSE_V3] Очистка старых данных...")
            Dish.objects.all().delete()
            # Очищаем связи в DayMenu без удаления самих дней
            for day_menu in DayMenu.objects.all():
                day_menu.available_dishes.clear()
            DishSelection.objects.all().delete() # Также очищаем выбор пользователей
            print("[PARSE_V3] Старые данные очищены.")

            # Подготовка дней недели (оставляем существующие объекты DayMenu)
            days_map = {
                'Понедельник': DayMenu.objects.get_or_create(day='monday')[0],
                'Вторник': DayMenu.objects.get_or_create(day='tuesday')[0],
                'Среда': DayMenu.objects.get_or_create(day='wednesday')[0],
                'Четверг': DayMenu.objects.get_or_create(day='thursday')[0],
                'Пятница': DayMenu.objects.get_or_create(day='friday')[0]
            }
            print(f"[PARSE_V3] Дни недели подготовлены: {list(days_map.keys())}")

            # Находим реальные названия колонок дней недели в файле
            day_columns_mapping = {}
            file_columns = df.columns
            for day_key in days_map.keys():
                found = False
                for col_name in file_columns:
                    if day_key.lower() in str(col_name).lower():
                        day_columns_mapping[day_key] = col_name
                        found = True
                        break
                if not found:
                    print(f"[PARSE_V3] ВНИМАНИЕ: Колонка для дня '{day_key}' не найдена в заголовках файла!")
            
            if not day_columns_mapping:
                 raise ValueError("Не найдены колонки с днями недели во второй строке файла.")
            print(f"[PARSE_V3] Сопоставление дней недели с колонками файла: {day_columns_mapping}")

            # Категории блюд (из первого столбца)
            # Ключ - как в Excel (в верхнем регистре), значение - внутренний код
            internal_categories = {
                'САЛАТЫ': 'salad',
                'СУПЫ': 'soup',
                'ГОРЯЧЕЕ': 'main',
                'ГАРНИРЫ': 'side',
                'ВЫПЕЧКА': 'bakery',
                # Добавьте другие категории при необходимости
                'ПОСТНЫЙ': 'fasting' # Если есть отдельная категория для постных
            }
            print(f"[PARSE_V3] Внутренние категории: {internal_categories}")

            # Определяем имя первого столбца (категории)
            category_column_name = df.columns[0]
            print(f"[PARSE_V3] Колонка категорий: '{category_column_name}'")

            # Заполняем пропуски в колонке категорий (из-за объединенных ячеек)
            # Преобразуем пустые строки в NaN перед ffill
            df[category_column_name] = df[category_column_name].replace('', pd.NA)
            df[category_column_name] = df[category_column_name].ffill()
            print("[PARSE_V3] Пропуски в колонке категорий заполнены (ffill).")
            # print("[PARSE_V3] DataFrame после ffill:")
            # print(df.head().to_string())

            # --- Обработка строк с блюдами ---
            dishes_added_total = 0
            dishes_by_day_count = {day: 0 for day in days_map.keys()}
            processed_rows = 0

            # Игнорируемый текст
            ignore_texts = ["гарнир выбирать не нужно"]

            for index, row in df.iterrows():
                processed_rows += 1
                row_num_display = index + 3 # +1 за 0-индекс, +2 за пропущенные строки заголовка
                
                # Получаем категорию для текущей строки
                category_raw = str(row[category_column_name]).strip().upper()
                current_internal_category = internal_categories.get(category_raw)

                if not current_internal_category:
                    # Пропускаем строки, если категория не распознана или это могут быть пустые строки в конце
                    if category_raw: # Печатаем только если там было какое-то значение
                         print(f"[PARSE_V3] Строка {row_num_display}: Неизвестная категория '{category_raw}', пропускаем.")
                    continue # Пропускаем строку, если категория не найдена

                print(f"[PARSE_V3] Строка {row_num_display}: Категория '{category_raw}' -> '{current_internal_category}'")

                # Обрабатываем блюда для каждого дня недели
                for day_key, actual_col_name in day_columns_mapping.items():
                    if actual_col_name not in df.columns:
                        continue # Пропускаем, если колонки нет

                    cell_value = str(row[actual_col_name]).strip()

                    # Пропускаем пустые ячейки или ячейки с игнорируемым текстом
                    if not cell_value or cell_value.lower() == 'nan' or cell_value.lower() in ignore_texts:
                        continue

                    print(f"[PARSE_V3]  День '{day_key}', Ячейка '{actual_col_name}': \"{cell_value}\"")

                    # Разбиваем ячейку на отдельные блюда по переводу строки
                    dishes_in_cell = [d.strip() for d in cell_value.split('\\n') if d.strip()]
                    
                    for dish_text in dishes_in_cell:
                        try:
                            # Извлекаем название и описание
                            dish_name = dish_text
                            description = ""
                            start_idx = dish_text.find('(')
                            end_idx = dish_text.rfind(')')

                            if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                                dish_name = dish_text[:start_idx].strip()
                                description = dish_text[start_idx + 1:end_idx].strip()
                            
                            # Дополнительная очистка имени
                            dish_name = dish_name.strip().strip('"').strip("'").strip()
                            
                            if not dish_name:
                                print(f"[PARSE_V3]    Пропуск: Пустое название блюда после обработки '{dish_text}'")
                                continue

                            # Определяем постность (по ключевым словам в тексте блюда)
                            is_fasting = any(word in dish_text.lower() for word in ['постное', 'постный', 'постная'])
                            
                            # Если категория "ПОСТНЫЙ", то блюдо точно постное
                            final_category_code = current_internal_category
                            if current_internal_category == 'fasting':
                                is_fasting = True
                            # Если нашли слово "постн*" в тексте, но категория не 'fasting',
                            # можно либо оставить исходную категорию, либо переопределить в 'fasting'.
                            # Пока оставляем исходную, но ставим флаг is_fasting = True.
                            
                            print(f"[PARSE_V3]    Блюдо: '{dish_name}', Описание: '{description}', Категория: {final_category_code}, Постное: {is_fasting}")

                            # Создаем или обновляем блюдо в БД
                            dish_obj, created = Dish.objects.get_or_create(
                                name=dish_name,
                                defaults={
                                    'category': final_category_code,
                                    'is_fasting': is_fasting,
                                    'description': description
                                }
                            )

                            if not created:
                                # Если блюдо уже есть, обновляем его данные на всякий случай
                                dish_obj.category = final_category_code
                                dish_obj.is_fasting = is_fasting
                                dish_obj.description = description
                                dish_obj.save()
                                print(f"[PARSE_V3]      Обновлено существующее блюдо ID {dish_obj.id}")
                            else:
                                print(f"[PARSE_V3]      Создано новое блюдо ID {dish_obj.id}")

                            # Добавляем блюдо в меню соответствующего дня
                            day_menu_obj = days_map[day_key]
                            day_menu_obj.available_dishes.add(dish_obj)
                            
                            # Увеличиваем счетчики
                            dishes_added_total += 1
                            # Считаем уникальные добавления блюда в день
                            dishes_by_day_count[day_key] += 1


                        except Exception as e:
                            print(f"[PARSE_V3]      ОШИБКА при обработке блюда '{dish_text}': {str(e)}")
                            traceback.print_exc()

            # --- Завершение парсинга ---
            print("-" * 30)
            print(f"[PARSE_V3] Обработка файла завершена.")
            print(f"[PARSE_V3] Всего обработано строк DataFrame (после заголовка): {processed_rows}")
            print(f"[PARSE_V3] Всего добавлено/обновлено блюд (связей с днями): {dishes_added_total}")
            print(f"[PARSE_V3] Распределение добавленных блюд по дням: {dishes_by_day_count}")

            # Проверка количества блюд по дням (установите ожидаемое число)
            expected_dishes_per_day = 21 # Установите ваше ожидаемое число
            for day, count in dishes_by_day_count.items():
                 if count != expected_dishes_per_day:
                     print(f"[PARSE_V3] ВНИМАНИЕ: День '{day}' имеет {count} блюд (ожидалось {expected_dishes_per_day}).")

            cache.clear() # Очищаем кэш Django
            messages.success(request, f'Успешно загружено и обработано {dishes_added_total} блюд(а) по дням.', extra_tags='shown')

        except ValueError as ve:
            messages.error(request, f'Ошибка в структуре файла: {str(ve)}')
            print(f"[PARSE_V3] Ошибка ValueError: {str(ve)}")
            traceback.print_exc()
        except Exception as e:
            messages.error(request, f'Произошла непредвиденная ошибка при обработке файла: {str(e)}')
            print(f"[PARSE_V3] Непредвиденная Ошибка Exception: {str(e)}")
            traceback.print_exc()

        return redirect('meal_planner:index')

    # Если метод не POST или нет файла
    return redirect('meal_planner:index')


@user_passes_test(is_admin)
def clear_calendar(request):
    """Очистка календаря"""
    try:
        print("[CLEAR] Начинаем очистку календаря...")
        
        # Очищаем все выборы блюд
        dish_selections_count = DishSelection.objects.count()
        DishSelection.objects.all().delete()
        print(f"[CLEAR] Удалено {dish_selections_count} выборов блюд")
        
        # Очищаем все сохраненные выборы
        user_selections_count = UserSelection.objects.count()
        UserSelection.objects.all().delete()
        print(f"[CLEAR] Удалено {user_selections_count} сохраненных выборов")
        
        # Очищаем все блюда
        dishes_count = Dish.objects.count()
        Dish.objects.all().delete()
        print(f"[CLEAR] Удалено {dishes_count} блюд")
        
        # Очищаем кэш
        cache.clear()
        print("[CLEAR] Кэш очищен")
        
        # Очищаем все сообщения
        storage = messages.get_messages(request)
        storage.used = True
        
        # Добавляем новое сообщение с тегом
        messages.success(request, 'Календарь успешно очищен', extra_tags='shown')
        print("[CLEAR] Очистка календаря завершена успешно")
    except Exception as e:
        print(f"[CLEAR] Ошибка при очистке календаря: {str(e)}")
        messages.error(request, f'Ошибка при очистке календаря: {str(e)}')
    
    return redirect('meal_planner:index')


@login_required
@user_passes_test(is_admin)
def delete_user(request, user_id):
    """Удаление пользователя (только для root)"""
    if request.user.id == user_id:
        messages.error(request, 'Нельзя удалить самого себя')
        return redirect('meal_planner:manage_users')
    
    try:
        user_to_delete = User.objects.get(id=user_id)
        if user_to_delete.username == 'root':
            messages.error(request, 'Нельзя удалить root пользователя')
            return redirect('meal_planner:manage_users')
            
        user_to_delete.delete()
        if not any(message.tags == 'success' for message in messages.get_messages(request)):
            messages.success(request, f'Пользователь {user_to_delete.username} успешно удален')
    except User.DoesNotExist:
        messages.error(request, 'Пользователь не найден')
    except Exception as e:
        messages.error(request, f'Произошла ошибка при удалении пользователя: {str(e)}')
    
    return redirect('meal_planner:manage_users')


@login_required
@user_passes_test(is_admin)
def make_admin(request, user_id):
    """Назначение пользователя администратором"""
    try:
        user = User.objects.get(id=user_id)
        if user.username == 'root':
            messages.error(request, 'Нельзя изменить права root пользователя')
            return redirect('meal_planner:manage_users')
        
        if request.method == 'POST':
            form = AdminPasswordForm(request.POST)
            if form.is_valid():
                password = form.cleaned_data['admin_password']
                user.set_password(password)
                user.is_superuser = True
                user.is_staff = True
                user.save()
                if not any(message.tags == 'success' for message in messages.get_messages(request)):
                    messages.success(request, f'Пользователь {user.username} назначен администратором')
                return redirect('meal_planner:manage_users')
        else:
            form = AdminPasswordForm()
        
        return render(request, 'meal_planner/make_admin.html', {
            'form': form,
            'user': user
        })
    except User.DoesNotExist:
        messages.error(request, 'Пользователь не найден')
        return redirect('meal_planner:manage_users')


@login_required
@user_passes_test(is_admin)
def remove_admin(request, user_id):
    """Снятие прав администратора (только для root)"""
    try:
        user = User.objects.get(id=user_id)
        if user.username == 'root':
            messages.error(request, 'Нельзя изменить права root пользователя')
            return redirect('meal_planner:manage_users')
            
        user.is_superuser = False
        user.is_staff = False
        user.save()
        if not any(message.tags == 'success' for message in messages.get_messages(request)):
            messages.success(request, f'Права администратора сняты с пользователя {user.username}')
    except User.DoesNotExist:
        messages.error(request, 'Пользователь не найден')
    except Exception as e:
        messages.error(request, f'Произошла ошибка: {str(e)}')
    
    return redirect('meal_planner:manage_users')


@login_required
@user_passes_test(is_admin)
def export_summary(request):
    """Выгрузка сводной информации в Excel"""
    try:
        # Создаем Excel файл
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        
        # Создаем лист с общим количеством блюд
        dishes_sheet = workbook.add_worksheet('Общее количество блюд')
        dishes_sheet.set_column('A:B', 30)
        
        # Заголовки
        dishes_sheet.write('A1', 'Название блюда')
        dishes_sheet.write('B1', 'Количество выборов')
        
        # Получаем все блюда и их количество выборов
        dishes = Dish.objects.all()
        dish_counts = {}
        for dish in dishes:
            count = DishSelection.objects.filter(dish=dish).count()
            dish_counts[dish.name] = count
        
        # Сортируем блюда по количеству выборов
        sorted_dishes = sorted(dish_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Записываем данные
        row = 1
        for dish_name, count in sorted_dishes:
            dishes_sheet.write(row, 0, dish_name)
            dishes_sheet.write(row, 1, count)
            row += 1
        
        # Создаем лист с выборками пользователей
        users_sheet = workbook.add_worksheet('Выборки пользователей')
        users_sheet.set_column('A:A', 20)
        users_sheet.set_column('B:B', 30)
        
        # Заголовки
        users_sheet.write('A1', 'Пользователь')
        users_sheet.write('B1', 'Выбранные блюда')
        
        # Получаем всех пользователей и их выборки
        users = User.objects.all()
        row = 1
        for user in users:
            selections = DishSelection.objects.filter(user=user)
            if selections.exists():
                dish_names = [selection.dish.name for selection in selections]
                users_sheet.write(row, 0, user.username)
                users_sheet.write(row, 1, ', '.join(dish_names))
                row += 1
        
        workbook.close()
        output.seek(0)
        
        # Создаем ответ
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=summary.xlsx'
        
        return response
    except Exception as e:
        messages.error(request, f'Произошла ошибка при выгрузке: {str(e)}')
        return redirect('meal_planner:manage_users')


@login_required
def save_selections(request, day_id):
    """Сохранение выбора блюд на день"""
    try:
        day_menu = DayMenu.objects.get(id=day_id)
        
        # Добавляем отладочную информацию о POST-данных
        print(f"[SAVE] POST данные: {request.POST}")
        print(f"[SAVE] Все ключи POST: {request.POST.keys()}")
        
        selected_dish_ids = request.POST.getlist('selected_dishes')
        
        print(f"[SAVE] Сохранение выбора для дня {day_menu.get_day_display()} (ID:{day_id})")
        print(f"[SAVE] Выбрано блюд: {len(selected_dish_ids)}")
        print(f"[SAVE] ID выбранных блюд: {selected_dish_ids}")
        
        # Преобразуем все ID в строки для сравнения
        selected_dish_ids = [str(id) for id in selected_dish_ids]
        
        # Получаем текущие выборы пользователя
        current_selections = DishSelection.objects.filter(
            user=request.user,
            day_menu=day_menu
        )
        
        print(f"[SAVE] Текущие выборы пользователя: {current_selections.count()}")
        
        # Обновляем существующие выборы
        for selection in current_selections:
            dish_id_str = str(selection.dish.id)
            if dish_id_str in selected_dish_ids:
                selection.selected = True
                selection.saved = True
                selection.saved_at = timezone.now()
                selection.save()
                # Безопасно удаляем ID из списка
                if dish_id_str in selected_dish_ids:
                    selected_dish_ids.remove(dish_id_str)
                print(f"[SAVE] Обновлено блюдо: {selection.dish.name} (ID:{dish_id_str})")
            else:
                selection.selected = False
                selection.save()
                print(f"[SAVE] Отменен выбор блюда: {selection.dish.name} (ID:{dish_id_str})")
        
        # Создаем новые выборы для оставшихся блюд
        for dish_id in selected_dish_ids:
            try:
                dish = Dish.objects.get(id=dish_id)
                # Используем get_or_create вместо create, чтобы избежать дублирования
                selection, created = DishSelection.objects.get_or_create(
                    user=request.user,
                    day_menu=day_menu,
                    dish=dish,
                    defaults={
                        'selected': True,
                        'saved': True,
                        'saved_at': timezone.now()
                    }
                )
                
                if created:
                    print(f"[SAVE] Создано новое блюдо: {dish.name} (ID:{dish.id})")
                else:
                    print(f"[SAVE] Блюдо уже существует: {dish.name} (ID:{dish.id})")
            except Dish.DoesNotExist:
                print(f"[SAVE] Блюдо не найдено: ID:{dish_id}")
                continue
            except Exception as e:
                print(f"[SAVE] Ошибка при создании выбора для блюда ID:{dish_id}: {str(e)}")
                continue
        
        # Очищаем кэш для этого дня и для календаря
        cache.delete(f'day_meals_{day_id}_{request.user.id}')
        cache.delete(f'calendar_view_{request.user.id}')
        print("[SAVE] Кэш очищен")
        
        # Проверяем, является ли запрос AJAX-запросом
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': 'Выбор блюд успешно сохранен'
            })
        
        messages.success(request, 'Выбор блюд успешно сохранен')
        return redirect('meal_planner:index')
        
    except DayMenu.DoesNotExist:
        print(f"[SAVE] Ошибка: День с ID {day_id} не найден")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': f'День с ID {day_id} не найден'
            })
        messages.error(request, f'День с ID {day_id} не найден')
        return redirect('meal_planner:index')
    except Exception as e:
        print(f"[SAVE] Ошибка: {str(e)}")
        import traceback
        print(f"[SAVE] Трассировка: {traceback.format_exc()}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': f'Произошла ошибка при сохранении: {str(e)}'
            })
        messages.error(request, f'Произошла ошибка при сохранении: {str(e)}')
        return redirect('meal_planner:index')


@login_required
def load_selection(request, selection_id):
    try:
        selection = UserSelection.objects.get(id=selection_id, user=request.user)
        # Загрузка сохраненного выбора
        messages.success(request, 'Выбор успешно загружен')
        return redirect('meal_planner:index')
    except UserSelection.DoesNotExist:
        messages.error(request, 'Выбор не найден')
        return redirect('meal_planner:view_saved_selections')


@login_required
def delete_selection(request, selection_id):
    try:
        selection = UserSelection.objects.get(id=selection_id, user=request.user)
        selection.delete()
        if not any(message.tags == 'success' for message in messages.get_messages(request)):
            messages.success(request, 'Выбор успешно удален')
    except UserSelection.DoesNotExist:
        messages.error(request, 'Выбор не найден')
    return redirect('meal_planner:view_saved_selections')


@login_required
def view_saved_selections(request):
    selections = UserSelection.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'meal_planner/saved_selections.html', {'selections': selections})


@login_required
def select_dishes_for_day(request, day_id):
    """Выбор нескольких блюд на день"""
    day_menu = get_object_or_404(DayMenu, id=day_id)
    user_id = request.GET.get('user_id')
    
    if user_id:
        user = get_object_or_404(User, id=user_id)
    else:
        user = request.user
    
    if request.method == 'POST':
        form = DishSelectionForm(request.POST, day_menu=day_menu, user=user)
        if form.is_valid():
            # Удаляем старые выборы пользователя для этого дня
            DishSelection.objects.filter(user=user, day_menu=day_menu).delete()
            
            # Создаем новые выборы
            for dish in form.cleaned_data['dishes']:
                DishSelection.objects.create(
                    user=user,
                    day_menu=day_menu,
                    dish=dish,
                    selected=True,
                    saved=True,
                    saved_at=timezone.now()
                )
            
            messages.success(request, 'Выбор блюд успешно сохранен')
            return redirect('meal_planner:index')
    else:
        current_selections = DishSelection.objects.filter(
            user=user,
            day_menu=day_menu,
            selected=True
        ).values_list('dish_id', flat=True)
        
        form = DishSelectionForm(
            day_menu=day_menu,
            user=user,
            initial={'dishes': current_selections}
        )
    
    return render(request, 'meal_planner/select_dish.html', {
        'day_menu': day_menu,
        'form': form,
        'selected_user': user if user_id else None
    })


@login_required
@user_passes_test(is_admin)
def change_password(request, user_id):
    """Изменение пароля пользователя"""
    try:
        user = User.objects.get(id=user_id)
        if request.method == 'POST':
            form = ChangePasswordForm(request.POST)
            if form.is_valid():
                password = form.cleaned_data['new_password1']
                user.set_password(password)
                user.save()
                messages.success(request, f'Пароль пользователя {user.username} успешно изменен')
                return redirect('meal_planner:manage_users')
        else:
            form = ChangePasswordForm()
        
        return render(request, 'meal_planner/change_password.html', {
            'form': form,
            'user': user
        })
    except User.DoesNotExist:
        messages.error(request, 'Пользователь не найден')
        return redirect('meal_planner:manage_users')


@login_required
def dishes_view(request):
    """Страница со списком всех блюд"""
    dishes = Dish.objects.all().order_by('category', 'name')
    
    # Группируем блюда по категориям
    categories = {}
    for dish in dishes:
        if dish.category not in categories:
            categories[dish.category] = []
        categories[dish.category].append(dish)
    
    # Добавляем иконки для категорий
    category_icons = {
        'salad': 'leaf',
        'soup': 'utensils',
        'main': 'fire',
        'side': 'carrot',
        'bakery': 'bread-slice',
        'fasting': 'leaf'
    }
    
    # Создаем словарь с информацией о категориях
    dish_categories = {}
    for code, name in Dish.DISH_CATEGORIES:
        dish_categories[code] = {
            'name': name,
            'icon': category_icons.get(code, 'question'),
            'dishes': categories.get(code, [])
        }
    
    return render(request, 'meal_planner/dishes.html', {
        'categories': dish_categories,
    })