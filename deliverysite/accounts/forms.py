from django import forms
from django.contrib.auth.forms import UserCreationForm
from delivery.models import User
from django.utils.safestring import mark_safe

class RegistrationForm(UserCreationForm):
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        label='Email'
    )
    first_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Имя'
    )
    last_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Фамилия'
    )
    phone = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7 (XXX) XXX-XX-XX'}),
        label='Телефон',
        required=True
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='Пароль'
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='Подтверждение пароля'
    )
    
    agree_to_terms = forms.BooleanField(
            required=True,
            label=mark_safe('Согласен(-на) на обработку персональных данных на сайте согласно <a href="/privacy-policy/" target="_blank">политике</a>'),
            error_messages={'required': 'Необходимо согласие на обработку персональных данных'},
            widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'phone', 'password1', 'password2']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Пользователь с таким email уже существует')
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = None
        user.role = 'client'
        
        if commit:
            user.save()
        
        return user