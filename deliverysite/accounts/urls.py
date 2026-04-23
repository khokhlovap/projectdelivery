from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.client_dashboard, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('company-setup/', views.company_setup, name='company_setup'),
    path('clients_orders/', views.client_orders, name='clients_orders'),
    path('check-order-rating/', views.check_order_rating, name='check_order_rating'),
    path('settings/', views.client_settings, name='client_settings'),
    path('ai-assistant/', views.ai_assistant, name='ai_assistant'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('manager/', views.manager_dashboard, name='manager_dashboard'),
    path('manager/tasks/', views.manager_tasks, name='manager_tasks'),
    path('manager/orders/', views.manager_orders, name='manager_orders'),
    path('rate-order/', views.rate_order, name='rate_order'),
    path('manager/couriers/', views.manager_couriers, name='manager_couriers'),
    path('manager/couriers/add/', views.manager_courier_add, name='manager_courier_add'),
    path('manager/couriers/<int:user_id>/edit/', views.manager_courier_edit, name='manager_courier_edit'),
    path('manager/couriers/<int:user_id>/detail/', views.manager_courier_detail, name='manager_courier_detail'),
    path('manager/clients/', views.manager_clients, name='manager_clients'),
    path('manager/clients/add/', views.manager_client_add, name='manager_client_add'),
    path('manager/clients/<int:user_id>/edit/', views.manager_client_edit, name='manager_client_edit'),
    path('manager/clients/<int:user_id>/detail/', views.manager_client_detail, name='manager_client_detail'),
    path('manager/reports/', views.manager_reports, name='manager_reports'),
    path('manager/settings/', views.manager_settings, name='manager_settings'),
    path('api/manager/notifications/', views.manager_notifications, name='manager_notifications'),
    path('api/manager/tasks/count/', views.manager_tasks_count, name='manager_tasks_count'),
    path('api/assign-courier/', views.assign_courier_ajax, name='assign_courier_ajax'),
    path('api/delete-order/', views.delete_order_ajax, name='delete_order_ajax'),
    path('api/order-details/', views.get_order_details, name='get_order_details'),
    path('api/ai-chat-stats/', views.ai_chat_stats, name='ai_chat_stats'),
    path('manager/ai-stats/', views.manager_ai_stats, name='manager_ai_stats'),
    path('api/ai-chat-last-queries/', views.ai_chat_last_queries, name='ai_chat_last_queries'),
]