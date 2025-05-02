from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.exceptions import ValidationError

class CustomUser(AbstractUser):
    is_admin = models.BooleanField(default=False)
    created_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)

class FoodCategory(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Категория блюд'
        verbose_name_plural = 'Категории блюд'

class Meal(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True, help_text="Полное описание блюда с ингредиентами")
    category = models.ForeignKey(FoodCategory, on_delete=models.CASCADE)
    is_complete_dish = models.BooleanField(default=False, help_text="Является ли блюдо полноценным (не требует гарнира)")
    excel_row = models.IntegerField(null=True, blank=True, help_text="Строка в Excel для этого блюда")
    
    def __str__(self):
        if self.description:
            return f"{self.name} ({self.description})"
        return self.name
    
    class Meta:
        verbose_name = 'Блюдо'
        verbose_name_plural = 'Блюда'
        ordering = ['category', 'excel_row', 'name']

class DayMenu(models.Model):
    DAYS_OF_WEEK = [
        (0, 'Понедельник'),
        (1, 'Вторник'),
        (2, 'Среда'),
        (3, 'Четверг'),
        (4, 'Пятница'),
    ]
    
    date = models.DateField()
    salads = models.ManyToManyField(Meal, related_name='day_menus_as_salad', blank=True, 
                                  limit_choices_to={'category__name': 'Салаты'})
    soups = models.ManyToManyField(Meal, related_name='day_menus_as_soup', blank=True,
                                 limit_choices_to={'category__name': 'Супы'})
    main_courses = models.ManyToManyField(Meal, related_name='day_menus_as_main', blank=True,
                                       limit_choices_to={'category__name': 'Горячие блюда'})
    sides = models.ManyToManyField(Meal, related_name='day_menus_as_side', blank=True,
                                limit_choices_to={'category__name': 'Гарниры'})
    bakery = models.ManyToManyField(Meal, related_name='day_menus_as_bakery', blank=True,
                                 limit_choices_to={'category__name': 'Выпечка'})
    
    def get_day(self):
        return self.date.weekday()
    
    def get_day_display(self):
        return dict(self.DAYS_OF_WEEK)[self.get_day()]
    
    def __str__(self):
        return f"{self.get_day_display()} ({self.date})"
    
    class Meta:
        verbose_name = 'Меню на день'
        verbose_name_plural = 'Меню по дням'
        ordering = ['date']

class UserSelection(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    day_menu = models.ForeignKey(DayMenu, on_delete=models.CASCADE)
    not_eating = models.BooleanField(default=False)
    selected_salad = models.ForeignKey(Meal, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='selected_as_salad')
    selected_soup = models.ForeignKey(Meal, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='selected_as_soup')
    selected_main = models.ForeignKey(Meal, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='selected_as_main')
    selected_side = models.ForeignKey(Meal, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='selected_as_side')
    selected_bakery = models.ForeignKey(Meal, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='selected_as_bakery')
    
    def clean(self):
        if self.not_eating:
            if any([self.selected_salad, self.selected_soup, self.selected_main, 
                   self.selected_side, self.selected_bakery]):
                raise ValidationError("Если выбрано 'НЕ ЕМ', нельзя выбирать блюда")
        
        if self.selected_main and self.selected_main.is_complete_dish and self.selected_side:
            raise ValidationError("Нельзя выбрать гарнир к полноценному блюду")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = 'Выбор пользователя'
        verbose_name_plural = 'Выборы пользователей'
        unique_together = ['user', 'day_menu']
        ordering = ['day_menu', 'user']
    
    def __str__(self):
        return f"{self.user.username} - {self.day_menu}"