from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Meal, UserSelection

class UserRegistrationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Имя пользователя'
        self.fields['username'].help_text = 'Обязательное поле. Только буквы, цифры и символы @/./+/-/_'
        self.fields['password1'].label = 'Пароль'
        self.fields['password1'].help_text = ''
        self.fields['password2'].label = 'Подтверждение пароля'
        self.fields['password2'].help_text = ''
        self.fields['is_admin'].label = 'Права администратора'

    class Meta:
        model = CustomUser
        fields = ('username', 'password1', 'password2', 'is_admin')

class MealUploadForm(forms.ModelForm):
    class Meta:
        model = Meal
        fields = ['name', 'category', 'description']
        
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and not (user.is_admin or user.is_superuser):
            self.fields['is_complete_dish'].widget.attrs['disabled'] = True
            self.fields['is_complete_dish'].help_text = 'Только администратор может изменять этот параметр'

class UserSelectionForm(forms.ModelForm):
    class Meta:
        model = UserSelection
        fields = ['selected_salad', 'selected_soup', 'selected_main', 'selected_side', 'selected_bakery', 'not_eating']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        if instance:
            day_menu = instance.day_menu
            self.fields['selected_salad'].queryset = day_menu.salads.all()
            self.fields['selected_soup'].queryset = day_menu.soups.all()
            self.fields['selected_main'].queryset = day_menu.main_courses.all()
            self.fields['selected_side'].queryset = day_menu.sides.all()
            self.fields['selected_bakery'].queryset = day_menu.bakery.all() 