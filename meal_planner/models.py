from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Категории блюд
DISH_CATEGORIES = [
    ('salad', 'Салаты'),
    ('soup', 'Супы'),
    ('main', 'Горячее'),
    ('side', 'Гарниры'),
    ('bakery', 'Выпечка'),
    ('fasting', 'Постная еда'),
]

class Dish(models.Model):
    name = models.CharField(max_length=200, verbose_name='Название блюда')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    category = models.CharField(
        max_length=20,
        choices=DISH_CATEGORIES,
        default='main',
        verbose_name='Категория'
    )
    is_fasting = models.BooleanField(default=False, verbose_name='Постное блюдо')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Блюдо'
        verbose_name_plural = 'Блюда'
        ordering = ['name']

class DayMenu(models.Model):
    DAY_CHOICES = [
        ('monday', 'Понедельник'),
        ('tuesday', 'Вторник'),
        ('wednesday', 'Среда'),
        ('thursday', 'Четверг'),
        ('friday', 'Пятница'),
    ]

    day = models.CharField(max_length=10, choices=DAY_CHOICES)
    dishes = models.ManyToManyField(Dish, through='DishSelection')
    available_dishes = models.ManyToManyField(Dish, related_name='available_in_days')

    def __str__(self):
        return self.get_day_display()

class DishSelection(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    day_menu = models.ForeignKey(DayMenu, on_delete=models.CASCADE)
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE)
    selected = models.BooleanField(default=False)
    saved = models.BooleanField(default=False, verbose_name='Сохранено')
    saved_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата сохранения')

    class Meta:
        unique_together = ('user', 'day_menu', 'dish')
        verbose_name = 'Выбор блюда'
        verbose_name_plural = 'Выборы блюд'

    def __str__(self):
        return f"{self.user.username} - {self.day_menu} - {self.dish.name}"

class UserSelection(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='selections')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Сохраненный выбор'
        verbose_name_plural = 'Сохраненные выборы'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.user.username})'

class SavedDishSelection(models.Model):
    selection = models.ForeignKey(UserSelection, on_delete=models.CASCADE, related_name='dishes')
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Сохраненное блюдо'
        verbose_name_plural = 'Сохраненные блюда'

    def __str__(self):
        return f'{self.dish.name} ({self.quantity})'