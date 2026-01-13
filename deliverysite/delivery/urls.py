from django.urls import path
from . import views

urlpatterns = [
    path('orders/create/', views.create_order, name='order_create'),
]
