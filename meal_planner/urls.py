from django.urls import path
from . import views

app_name = 'meal_planner'

urlpatterns = [
    path('', views.calendar_view, name='index'),
    path('dishes/', views.dishes_view, name='dishes'),
    path('day/<int:day_id>/', views.day_meals_view, name='day_meals'),
    path('select-dish/<int:day_id>/<int:dish_id>/', views.select_dish, name='select_dish'),
    path('deselect-dish/<int:day_id>/<int:dish_id>/', views.deselect_dish, name='deselect_dish'),
    path('upload-excel/', views.upload_excel, name='upload_excel'),
    path('export-selections/<str:format>/', views.export_selections, name='export_selections'),
    path('clear-calendar/', views.clear_calendar, name='clear_calendar'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('make-admin/<int:user_id>/', views.make_admin, name='make_admin'),
    path('remove-admin/<int:user_id>/', views.remove_admin, name='remove_admin'),
    path('export-summary/', views.export_summary, name='export_summary'),
    path('save-selections/<int:day_id>/', views.save_selections, name='save_selections'),
    path('load-selection/<int:selection_id>/', views.load_selection, name='load_selection'),
    path('delete-selection/<int:selection_id>/', views.delete_selection, name='delete_selection'),
    path('saved-selections/', views.view_saved_selections, name='saved_selections'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('manage-users/', views.manage_users, name='manage_users'),
    path('change-password/<int:user_id>/', views.change_password, name='change_password'),
]