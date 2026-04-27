from django import forms
from .models import Order

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            'order_type',
            'tariff',
            'weight',
            'client_comment',
            'pickup_address',
            'delivery_address',
            'recipient_first_name',
            'recipient_last_name',
            'recipient_patronymic',
            'recipient_phone',
            'recipient_company',
            'requested_delivery_date',
            'requested_time_slot',  # ДОБАВИТЬ
        ]
        widgets = {
            'pickup_address': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'delivery_address': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'client_comment': forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'Дополнительная информация для курьера'}),
            'requested_delivery_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'requested_time_slot': forms.Select(attrs={'class': 'form-select'}), 
            'order_type': forms.Select(attrs={'class': 'form-select'}),
            'tariff': forms.Select(attrs={'class': 'form-select'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'recipient_first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'recipient_last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'recipient_patronymic': forms.TextInput(attrs={'class': 'form-control'}),
            'recipient_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'recipient_company': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'order_type': 'Тип заказа',
            'tariff': 'Тариф доставки',
            'weight': 'Вес (кг)',
            'client_comment': 'Комментарий к заказу',
            'pickup_address': 'Адрес отправления',
            'delivery_address': 'Адрес доставки',
            'recipient_first_name': 'Имя получателя',
            'recipient_last_name': 'Фамилия получателя',
            'recipient_patronymic': 'Отчество получателя',
            'recipient_phone': 'Телефон получателя',
            'recipient_company': 'Компания получателя',
            'requested_delivery_date': 'Желаемая дата доставки',
            'requested_time_slot': 'Желаемое время доставки',  # ДОБАВИТЬ
        }