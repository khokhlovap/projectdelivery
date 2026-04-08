from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.client_dashboard, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('company-setup/', views.company_setup, name='company_setup'),
    path('orders/', views.client_orders, name='orders'),
    path('settings/', views.client_settings, name='settings'),
    path('ai-assistant/', views.ai_assistant, name='ai_assistant'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
]