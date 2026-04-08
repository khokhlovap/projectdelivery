from django import forms
from .models import Order

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            'order_type', 'tariff', 'weight',
            'pickup_address', 'delivery_address',
            'recipient_first_name', 'recipient_last_name', 
            'recipient_patronymic', 'recipient_phone', 'recipient_company',
            'requested_delivery_date', 'client_comment'
        ]
        widgets = {
            'order_type': forms.Select(attrs={'class': 'form-select'}),
            'tariff': forms.Select(attrs={'class': 'form-select'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'pickup_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'delivery_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'recipient_first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'recipient_last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'recipient_patronymic': forms.TextInput(attrs={'class': 'form-control'}),
            'recipient_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'recipient_company': forms.TextInput(attrs={'class': 'form-control'}),
            'requested_delivery_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'client_comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'order_type': 'Тип заказа',
            'tariff': 'Тариф доставки',
            'weight': 'Вес (кг)',
            'pickup_address': 'Адрес отправки',
            'delivery_address': 'Адрес доставки',
            'recipient_first_name': 'Имя получателя',
            'recipient_last_name': 'Фамилия получателя',
            'recipient_patronymic': 'Отчество получателя',
            'recipient_phone': 'Телефон получателя',
            'recipient_company': 'Компания получателя',
            'requested_delivery_date': 'Желаемая дата доставки',
            'client_comment': 'Комментарий к заказу',
        }