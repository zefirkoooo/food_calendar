from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from .models import Dish, DayMenu, DishSelection, UserSelection, SavedDishSelection


class ExcelUploadForm(forms.Form):
    excel_file = forms.FileField(
        label='Выберите Excel файл',
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )


class SimpleUserCreationForm(forms.ModelForm):
    """Упрощенная форма создания пользователя"""
    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='Введите пароль'
    )
    password2 = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='Введите тот же пароль для подтверждения'
    )

    class Meta:
        model = User
        fields = ('username', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'})
        }

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Пароли не совпадают")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserSelectionForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        label='Пользователь',
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class DishSelectionForm(forms.Form):
    dishes = forms.ModelMultipleChoiceField(
        queryset=Dish.objects.none(),
        label='Блюда',
        widget=forms.SelectMultiple(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        day_id = kwargs.pop('day_id', None)
        super().__init__(*args, **kwargs)
        if day_id:
            day_menu = DayMenu.objects.get(id=day_id)
            self.fields['dishes'].queryset = day_menu.available_dishes.all()


class AdminPasswordForm(forms.Form):
    admin_password = forms.CharField(
        label='Пароль администратора',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=3,
        help_text='Минимум 3 символа'
    )


class ChangePasswordForm(forms.Form):
    new_password1 = forms.CharField(
        label='Новый пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=3,
        help_text='Минимум 3 символа'
    )
    new_password2 = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=3,
        help_text='Введите тот же пароль для подтверждения'
    )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Пароли не совпадают')

        return cleaned_data


class SaveSelectionForm(forms.ModelForm):
    class Meta:
        model = UserSelection
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'})
        }