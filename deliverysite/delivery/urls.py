from django.urls import path
from . import views

app_name = 'delivery'

urlpatterns = [
    path('create/', views.create_order, name='create_order'),
    path('orders/', views.order_list, name='order_list'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('order/<int:order_id>/assign/', views.assign_courier, name='assign_courier'),
    path('order/<int:order_id>/delete/', views.delete_order, name='delete_order'),
    path('courier/accept/<int:order_id>/', views.courier_accept_order, name='courier_accept_order'),
    path('courier/reject/<int:order_id>/', views.courier_reject_order, name='courier_reject_order'),
    path('order/<int:order_id>/complete/', views.complete_order, name='complete_order'),
    path('courier/dashboard/', views.courier_dashboard, name='courier_dashboard'),
    path('courier/active-orders/', views.courier_active_orders, name='courier_active_orders'),
    path('courier/profile/', views.courier_profile, name='courier_profile'),
    path('courier/update-shift/', views.courier_update_shift, name='courier_update_shift'),
    path('courier/accept/<int:order_id>/', views.courier_accept_order, name='courier_accept_order'),
    path('courier/reject/<int:order_id>/', views.courier_reject_order, name='courier_reject_order'),
    path('courier/active-count/', views.courier_active_count, name='courier_active_count'),
    path('courier/start-break/', views.courier_start_break, name='courier_start_break'),
    path('courier/end-break/', views.courier_end_break, name='courier_end_break'),
    path('courier/order/<int:order_id>/', views.courier_order_detail, name='courier_order_detail'),
    path('courier/update-order-status/', views.courier_update_order_status, name='courier_update_order_status'),
    path('courier/order/<int:order_id>/readonly/', views.courier_order_readonly, name='courier_order_readonly'),
    path('courier/settings/', views.courier_settings_menu, name='courier_settings_menu'),
    path('courier/settings/profile/', views.courier_settings_profile, name='courier_settings_profile'),
    path('courier/settings/statistics/', views.courier_settings_statistics, name='courier_settings_statistics'),
    path('courier/settings/history/', views.courier_settings_history, name='courier_settings_history'),
    path('courier/settings/security/', views.courier_settings_security, name='courier_settings_security'),
    path('courier/order/<int:order_id>/detail/', views.courier_order_detail_page, name='courier_order_detail_page'),
    path('courier/check-new-orders/', views.courier_check_new_orders, name='courier_check_new_orders'),
    path('courier/update-shift-with-slot/', views.courier_update_shift_with_slot, name='courier_update_shift_with_slot'),
]
