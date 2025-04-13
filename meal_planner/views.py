import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponse
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
            if user.username == 'root':
                return redirect('meal_planner:index')
            else:
                request.session['selected_user_id'] = user.id
                return redirect('meal_planner:index')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль')
    
    return render(request, 'meal_planner/login.html')


def logout_view(request):
    """Выход из системы"""
    if request.method == 'POST':
        # Очищаем всю сессию
        request.session.flush()
        logout(request)
        return redirect('meal_planner:login')
    else:
        # Если запрос не POST, перенаправляем на главную страницу
        return redirect('meal_planner:calendar')


def calendar_view(request):
    """Главная страница с календарем"""
    if not request.user.is_authenticated:
        return redirect('meal_planner:login')
    
    # Order days from Monday to Friday
    days = DayMenu.objects.all().order_by('day')
    day_order = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
    days = sorted(days, key=lambda x: day_order.index(x.day))

    upload_form = ExcelUploadForm()
    selected_user = request.user

    context = {
        'days': days,
        'upload_form': upload_form,
        'selected_user': selected_user,
    }

    return render(request, 'meal_planner/calendar.html', context)


@login_required
def day_meals_view(request, day_id):
    try:
        day_menu = DayMenu.objects.get(id=day_id)
        # Получаем все блюда, доступные для этого дня
        dishes = day_menu.available_dishes.all()
        
        # Получаем выборки текущего пользователя для этого дня
        user_selections = DishSelection.objects.filter(
            user=request.user,
            day_menu=day_menu,
            selected=True
        )
        selected_dishes = {selection.dish.id: selection for selection in user_selections}
        
        context = {
            'day': day_menu,
            'dishes': dishes,
            'selected_dishes': selected_dishes,
            'selected_user': request.user,
        }
        return render(request, 'meal_planner/day_meals.html', context)
    except DayMenu.DoesNotExist:
        messages.error(request, 'День не найден')
        return redirect('meal_planner:index')


@login_required
def select_dish(request, day_id, dish_id):
    """Выбор блюда на день"""
    try:
        day_menu = DayMenu.objects.get(id=day_id)
        dish = Dish.objects.get(id=dish_id)
        
        selection, created = DishSelection.objects.get_or_create(
            user=request.user,
            day_menu=day_menu,
            dish=dish,
            defaults={'selected': True}
        )
        
        if not created:
            selection.selected = True
            selection.save()
        
        # Не показываем сообщение, так как оно будет показано при сохранении
    except (DayMenu.DoesNotExist, Dish.DoesNotExist):
        messages.error(request, 'Блюдо или день не найдены')
    
    return redirect('meal_planner:day_meals', day_id=day_id)


@login_required
def deselect_dish(request, day_id, dish_id):
    try:
        selection = DishSelection.objects.get(
            user=request.user,
            day_menu_id=day_id,
            dish_id=dish_id
        )
        selection.selected = False
        selection.save()
        # Не показываем сообщение, так как оно будет показано при сохранении
    except DishSelection.DoesNotExist:
        messages.error(request, 'Выбор не найден')
    
    return redirect('meal_planner:day_meals', day_id=day_id)


@login_required
def upload_excel(request):
    if not request.user.is_superuser:
        messages.error(request, 'У вас нет прав для загрузки файлов')
        return redirect('meal_planner:index')
    
    if request.method == 'POST':
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                excel_file = request.FILES['excel_file']
                success_count = parse_excel_menu(excel_file)
                
                # Очищаем все сообщения
                storage = messages.get_messages(request)
                storage.used = True
                
                # Добавляем новое сообщение
                messages.success(request, f'Успешно загружено {success_count} записей')
                return redirect('meal_planner:index')
            except Exception as e:
                messages.error(request, f'Ошибка при загрузке файла: {str(e)}')
    else:
        form = ExcelUploadForm()
    
    return render(request, 'meal_planner/upload_excel.html', {'form': form})


@login_required
@user_passes_test(is_admin)
def clear_calendar(request):
    """Очистка календаря"""
    if not request.user.is_superuser:
        messages.error(request, 'У вас нет прав для очистки календаря')
        return redirect('meal_planner:index')
    
    try:
        # Очищаем все выборы блюд
        DishSelection.objects.all().delete()
        # Очищаем все сохраненные выборы
        UserSelection.objects.all().delete()
        # Очищаем все блюда
        Dish.objects.all().delete()
        
        # Очищаем все сообщения
        storage = messages.get_messages(request)
        storage.used = True
        
        # Добавляем новое сообщение
        messages.success(request, 'Календарь успешно очищен')
    except Exception as e:
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
        selected_dish_ids = request.POST.getlist('dishes')
        
        # Удаляем старые выборы пользователя для этого дня
        DishSelection.objects.filter(user=request.user, day_menu=day_menu).delete()
        
        # Создаем новые выборы
        for dish_id in selected_dish_ids:
            dish = Dish.objects.get(id=dish_id)
            DishSelection.objects.create(
                user=request.user,
                day_menu=day_menu,
                dish=dish,
                selected=True,
                saved=True,
                saved_at=timezone.now()
            )
        
        # Очищаем все сообщения
        storage = messages.get_messages(request)
        storage.used = True
        
        # Добавляем новое сообщение
        messages.success(request, 'Выбор блюд успешно сохранен')
    except Exception as e:
        messages.error(request, f'Ошибка при сохранении выбора: {str(e)}')
    
    return redirect('meal_planner:day_meals', day_id=day_id)


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