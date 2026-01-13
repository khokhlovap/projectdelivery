from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Role, UserProfile, Courier, Manager, OrderType, Order,
    OrderStatus, Payment, CourierRating, TelegramProfile, Vacation, AIChatLog
)
from django.utils.translation import gettext_lazy as _

# UserAdmin для модели User
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ['email']
    list_display = ['email', 'first_name', 'last_name', 'is_staff', 'is_active']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'groups']
    search_fields = ['email', 'first_name', 'last_name']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'patronymic', 'phone', 'birth_date')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )

# Регистрация моделей
admin.site.register(Role)
admin.site.register(UserProfile)
admin.site.register(Courier)
admin.site.register(Manager)
admin.site.register(OrderType)
admin.site.register(Order)
admin.site.register(OrderStatus)
admin.site.register(Payment)
admin.site.register(CourierRating)
admin.site.register(TelegramProfile)
admin.site.register(Vacation)
admin.site.register(AIChatLog)
