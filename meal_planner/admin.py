from django.contrib import admin
from .models import Dish, DayMenu, DishSelection

@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')

@admin.register(DayMenu)
class DayMenuAdmin(admin.ModelAdmin):
    list_display = ('get_day_display',)

@admin.register(DishSelection)
class DishSelectionAdmin(admin.ModelAdmin):
    list_display = ('user', 'day_menu', 'dish', 'selected')
    list_filter = ('user', 'day_menu', 'selected')
    search_fields = ('user__username', 'dish__name')