from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Dish',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='DayMenu',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('day', models.CharField(choices=[('monday', 'Понедельник'), ('tuesday', 'Вторник'), ('wednesday', 'Среда'), ('thursday', 'Четверг'), ('friday', 'Пятница')], max_length=10)),
            ],
        ),
        migrations.CreateModel(
            name='DishSelection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('selected', models.BooleanField(default=False)),
                ('day_menu', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='meal_planner.daymenu')),
                ('dish', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='meal_planner.dish')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'day_menu', 'dish')},
            },
        ),
        migrations.AddField(
            model_name='daymenu',
            name='available_dishes',
            field=models.ManyToManyField(related_name='available_in_days', to='meal_planner.dish'),
        ),
        migrations.AddField(
            model_name='daymenu',
            name='dishes',
            field=models.ManyToManyField(through='meal_planner.DishSelection', to='meal_planner.dish'),
        ),
    ] 