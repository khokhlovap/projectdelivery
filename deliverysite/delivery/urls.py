from django.urls import path
from . import views

app_name = 'delivery'

urlpatterns = [
    path('create/', views.create_order, name='create_order'),
    path('orders/', views.order_list, name='order_list'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('order/<int:order_id>/assign/', views.assign_courier, name='assign_courier'),
    path('order/<int:order_id>/delete/', views.delete_order, name='delete_order'),
]