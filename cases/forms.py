from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class CustomUserCreationForm(UserCreationForm):
    """Форма регистрации с дополнительными полями."""

    first_name = forms.CharField(
        max_length=50,
        required=True,
        label="Имя",
        widget=forms.TextInput(attrs={'placeholder': 'Введите ваше имя'})
    )

    last_name = forms.CharField(
        max_length=50,
        required=False,
        label="Фамилия",
        widget=forms.TextInput(attrs={'placeholder': 'Введите вашу фамилию'})
    )

    email = forms.EmailField(
        required=True,
        label="Email",
        widget=forms.EmailInput(attrs={'placeholder': 'example@mail.ru'})
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Убираем стандартные подсказки Django о пароле
        self.fields['password1'].help_text = ''
        self.fields['password2'].help_text = ''