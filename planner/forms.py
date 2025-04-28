from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile, DietType


class LoginForm(forms.Form):
    username = forms.CharField(
        label="Логин",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="Email",
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    username = forms.CharField(
        label="Логин",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text="Логин будет отображаться под аватаркой в личном кабинете"
    )
    password1 = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    password2 = forms.CharField(
        label="Подтверждение пароля",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    diet_type = forms.ModelChoiceField(
        queryset=DietType.objects.all(),
        required=False,
        label="Тип диеты",
        widget=forms.Select(attrs={'class': 'form-select'})
    )


    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Пользователь с таким email уже существует")
        return email


class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        label="Имя",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        label="Фамилия",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        label="Email",
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    budget_limit = forms.DecimalField(
        label='Бюджет на один приём пищи (руб)',
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
        })
    )
    avatar = forms.ImageField(
        label='Аватар',
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control d-none',
            'id': 'avatar-upload'
        })
    )

    class Meta:
        model = UserProfile
        fields = ['budget_limit', 'avatar']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['first_name'].initial = user.first_name
        self.fields['last_name'].initial = user.last_name
        self.fields['email'].initial = user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = self.instance.user

        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']

        if commit:
            user.save()
            profile.save()

        return profile
