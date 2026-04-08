from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from .models import (
    User, Client, ClientAdditionalInfo, Manager, Courier,
    CourierAdditionalInfo, Vacation, SickLeave, CourierShift,
    CourierShiftBreak, Order, OrderStatusHistory, OrderRating,
    Payment, AIChatKnowledgeBase, AIChatLog
)


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = '__all__'


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email',)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Личная информация', {'fields': ('first_name', 'last_name', 'patronymic', 'phone', 'birth_date')}),
        ('Роль и права', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'role'),
        }),
    )
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_active')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    list_filter = ('role', 'is_active', 'is_staff')


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'inn', 'city', 'company_phone')
    search_fields = ('company_name', 'inn', 'contact_person_email')
    list_filter = ('city',)


@admin.register(ClientAdditionalInfo)
class ClientAdditionalInfoAdmin(admin.ModelAdmin):
    list_display = ('client', 'created_at')
    search_fields = ('client__company_name',)


@admin.register(Manager)
class ManagerAdmin(admin.ModelAdmin):
    list_display = ('user', 'position')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')


@admin.register(Courier)
class CourierAdmin(admin.ModelAdmin):
    list_display = ('user', 'shift_status', 'total_orders', 'avg_rating')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    list_filter = ('shift_status', 'hire_date')


@admin.register(CourierAdditionalInfo)
class CourierAdditionalInfoAdmin(admin.ModelAdmin):
    list_display = ('courier', 'created_at')
    search_fields = ('courier__user__email',)


@admin.register(Vacation)
class VacationAdmin(admin.ModelAdmin):
    list_display = ('courier', 'start_date', 'end_date')
    search_fields = ('courier__user__email',)
    list_filter = ('start_date',)


@admin.register(SickLeave)
class SickLeaveAdmin(admin.ModelAdmin):
    list_display = ('courier', 'start_date', 'end_date')
    search_fields = ('courier__user__email',)
    list_filter = ('start_date',)


@admin.register(CourierShift)
class CourierShiftAdmin(admin.ModelAdmin):
    list_display = ('courier', 'start_time', 'end_time', 'orders_completed')
    search_fields = ('courier__user__email',)
    list_filter = ('start_time',)


@admin.register(CourierShiftBreak)
class CourierShiftBreakAdmin(admin.ModelAdmin):
    list_display = ('shift', 'start_time', 'end_time')
    search_fields = ('shift__courier__user__email',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'courier', 'status', 'created_at')
    search_fields = ('client__company_name', 'recipient_phone')
    list_filter = ('status', 'order_type', 'tariff', 'created_at')


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('order', 'status', 'changed_at')
    list_filter = ('status',)


@admin.register(OrderRating)
class OrderRatingAdmin(admin.ModelAdmin):
    list_display = ('order', 'courier', 'rating', 'created_at')
    list_filter = ('rating',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'status', 'created_at', 'paid_at')
    list_filter = ('status',)


@admin.register(AIChatKnowledgeBase)
class AIChatKnowledgeBaseAdmin(admin.ModelAdmin):
    list_display = ('question', 'created_at')
    search_fields = ('question', 'keywords')


@admin.register(AIChatLog)
class AIChatLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'question', 'created_at')
    search_fields = ('user__email', 'question')
    list_filter = ('created_at',)