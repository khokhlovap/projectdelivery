from django.urls import path
from . import views

urlpatterns = [
    path('orders/create/', views.create_order, name='order_create'),
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:order_id>/assign/', views.assign_courier, name='assign_courier'),
    path('orders/<int:order_id>/delete/', views.delete_order, name='delete_order'),
]