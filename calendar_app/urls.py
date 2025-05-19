from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views
from .views import update_complete_dish_status

urlpatterns = [
    path('', views.login_view, name='login'),
    path('home/', login_required(views.home), name='home'),
    path('day/<int:day_id>/', login_required(views.day_detail), name='day_detail'),
    path('user-management/', login_required(views.user_management), name='user_management'),
    path('create-user/', login_required(views.create_user), name='create_user'),
    path('export-selections/', login_required(views.export_selections), name='export_selections'),
    path('clear-calendar/', views.clear_calendar, name='clear_calendar'),
    path('change-password/', login_required(views.change_password), name='change_password'),
    path('change-password/<int:user_id>/', login_required(views.change_password), name='change_user_password'),
    path('export-data/', login_required(views.export_data), name='export_data'),
    path('update-complete-dish-status/', login_required(update_complete_dish_status), name='update_complete_dish_status'),
    path('manage_dishes/', login_required(views.manage_dishes), name='manage_dishes'),
    path('clear-all-dishes/', login_required(views.clear_all_dishes), name='clear_all_dishes'),
] 