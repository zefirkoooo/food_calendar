from django.urls import path
from . import views
from .views import update_complete_dish_status

urlpatterns = [
    path('', views.login_view, name='login'),
    path('home/', views.home, name='home'),
    path('day/<int:day_id>/', views.day_detail, name='day_detail'),
    path('user-management/', views.user_management, name='user_management'),
    path('create-user/', views.create_user, name='create_user'),
    path('export-selections/', views.export_selections, name='export_selections'),
    path('clear-calendar/', views.clear_calendar, name='clear_calendar'),
    path('change-password/', views.change_password, name='change_password'),
    path('change-password/<int:user_id>/', views.change_password, name='change_user_password'),
    path('export-data/', views.export_data, name='export_data'),
    path('update-complete-dish-status/', update_complete_dish_status, name='update_complete_dish_status'),
    path('manage_dishes/', views.manage_dishes, name='manage_dishes'),
    path('clear-all-dishes/', views.clear_all_dishes, name='clear_all_dishes'),
] 