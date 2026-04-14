from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse  
from django.utils import timezone  
from .forms import RegistrationForm
from django.contrib.auth.forms import AuthenticationForm
from delivery.models import Order, Client, Courier, OrderRating, OrderStatusHistory 
from django.db.models import Count, Avg, Q
from datetime import datetime, timedelta

# ЛК Клиент
def register_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:home')
    
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.get_full_name()}! Пожалуйста, заполните данные компании.')
            return redirect('accounts:company_setup')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')
    else:
        form = RegistrationForm()
    
    return render(request, 'registration/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:home')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            
            # Проверка роли пользователя и перенаправление
            if user.role == 'manager':
                messages.success(request, f'Добро пожаловать в панель управления, {user.get_full_name()}!')
                return redirect('accounts:manager_dashboard')
            elif user.role == 'client':
                try:
                    if user.client_profile:
                        messages.success(request, f'Добро пожаловать, {user.get_full_name()}!')
                        return redirect('accounts:home')
                except:
                    messages.warning(request, 'Пожалуйста, заполните данные компании')
                    return redirect('accounts:company_setup')
            elif user.role == 'courier':
                # Если добавите панель курьера
                return redirect('delivery:courier_dashboard')
        else:
            messages.error(request, 'Неверный email или пароль')
    else:
        form = AuthenticationForm()
    
    return render(request, 'registration/login.html', {'form': form})

def logout_view(request):
    "Выход из системы"
    logout(request)
    messages.info(request, 'Вы вышли из системы')
    return redirect('accounts:login')

@login_required
def company_setup(request):
    "Заполнение данных компании"
    try:
        client = request.user.client_profile
        return redirect('accounts:home')
    except:
        client = None
    
    if request.method == 'POST':
        Client.objects.create(
            user=request.user,
            company_name=request.POST.get('company_name'),
            inn=request.POST.get('inn'),
            kpp=request.POST.get('kpp'),
            legal_address=request.POST.get('legal_address'),
            actual_address=request.POST.get('actual_address'),
            company_phone=request.POST.get('company_phone'),
            company_email=request.POST.get('company_email'),
            bank=request.POST.get('bank'),
            settlement_account=request.POST.get('settlement_account'),
            correspondent_account=request.POST.get('correspondent_account'),
            contact_person_first_name=request.user.first_name,
            contact_person_last_name=request.user.last_name,
            contact_person_phone=request.user.phone,
            contact_person_email=request.user.email,
        )
        messages.success(request, 'Данные компании успешно сохранены! Теперь вы можете создавать заказы.')
        return redirect('accounts:home')
    
    return render(request, 'accounts/company_setup.html')

@login_required
def client_dashboard(request):
    "Главная страница личного кабинета"
    try:
        client_profile = request.user.client_profile
    except:
        messages.warning(request, 'Для создания заказов необходимо заполнить данные компании')
        return redirect('accounts:company_setup')
    
    try:
        active_orders = Order.objects.filter(
            client=client_profile,
            status__in=['created', 'pending', 'assigned', 'in_progress']
        ).order_by('-created_at')
        active_orders_count = active_orders.count()
        
        total_orders = Order.objects.filter(client=client_profile).count()
        delivered_count = Order.objects.filter(client=client_profile, status='delivered').count()
    except:
        active_orders = []
        active_orders_count = 0
        total_orders = 0
        delivered_count = 0
    
    context = {
        'active_orders': active_orders,
        'active_orders_count': active_orders_count,
        'total_orders': total_orders,
        'delivered_count': delivered_count,
    }
    return render(request, 'accounts/dashboard.html', context)

@login_required
def client_orders(request):
    "Все заказы клиента"
    try:
        orders = Order.objects.filter(
            client=request.user.client_profile
        ).order_by('-created_at')
    except:
        orders = []
    
    return render(request, 'accounts/orders.html', {'orders': orders})

@login_required
def client_settings(request):
    "Настройки профиля"
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.patronymic = request.POST.get('patronymic')
        user.phone = request.POST.get('phone')
        user.save()
        messages.success(request, 'Профиль успешно обновлен')
        return redirect('accounts:settings')
    
    return render(request, 'accounts/settings.html')

@login_required
def ai_assistant(request):
    "AI помощник"
    return render(request, 'accounts/ai_assistant.html')

def privacy_policy(request):
    "Страница с политикой конфиденциальности"
    return render(request, 'accounts/privacy_policy.html')

# ЛК Менеджер
@login_required
def manager_dashboard(request):
    """Главная страница менеджера"""
    if request.user.role != 'manager':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('accounts:home')
    
    # Активные заказы
    active_orders = Order.objects.filter(
        status__in=['created', 'pending', 'assigned', 'in_progress']
    ).count()
    
    # Новые заказы (ожидают назначения)
    new_orders = Order.objects.filter(status='pending').count()
    
    # Просроченные заказы (желаемая дата доставки уже прошла)
    from django.utils import timezone
    delayed_orders = Order.objects.filter(
        requested_delivery_date__lt=timezone.now().date(),
        status__in=['created', 'pending', 'assigned', 'in_progress']
    ).count()
    
    # Данные для графика за неделю
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    weekly_data = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        count = Order.objects.filter(created_at__date=day).count()
        weekly_data.append(count)
    
    # Топ курьеров по рейтингу
    top_couriers = []
    for courier in Courier.objects.filter(user__role='courier').order_by('-avg_rating')[:3]:
        deliveries_count = Order.objects.filter(courier=courier, status='delivered').count()
        top_couriers.append({
            'name': courier.user.get_full_name(),
            'deliveries': deliveries_count,
            'avg_time': 30,
            'rating': float(courier.avg_rating)
        })
    
    context = {
        'active_orders': active_orders,
        'new_orders': new_orders,
        'delayed_orders': delayed_orders,
        'weekly_data': weekly_data,
        'top_couriers': top_couriers,
    }
    return render(request, 'accounts/manager_dashboard.html', context)

@login_required
def manager_notifications(request):
    """API для получения уведомлений менеджера"""
    if request.user.role != 'manager':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    notifications = []
    
    # 1. Заказы без курьера (created или pending)
    orders_without_courier = Order.objects.filter(
        status__in=['created', 'pending']
    )
    
    for order in orders_without_courier[:5]:
        notifications.append({
            'type': 'warning',
            'message': f'Заказ №{order.id} ({order.get_status_display()}) ожидает назначения курьера',
            'time': order.created_at.strftime('%H:%M'),
            'order_id': order.id
        })
    
    # 2. Просроченные заказы
    from django.utils import timezone
    delayed_orders = Order.objects.filter(
        requested_delivery_date__lt=timezone.now().date(),
        status__in=['created', 'pending', 'assigned', 'in_progress']
    )
    
    for order in delayed_orders[:5]:
        days_delayed = (timezone.now().date() - order.requested_delivery_date).days
        notifications.append({
            'type': 'danger',
            'message': f'⚠️ Заказ №{order.id} просрочен на {days_delayed} дн.',
            'time': order.created_at.strftime('%H:%M'),
            'order_id': order.id
        })
    
    return JsonResponse({'notifications': notifications})

@login_required
def manager_tasks(request):
    """Страница задач менеджера"""
    if request.user.role != 'manager':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('accounts:home')
    
    # Заказы, требующие внимания (без курьера)
    orders_without_courier = Order.objects.filter(
        status__in=['created', 'pending']  # Создан или ожидает назначения
    )
    
    # Просроченные заказы
    from django.utils import timezone
    delayed_orders = Order.objects.filter(
        requested_delivery_date__lt=timezone.now().date(),
        status__in=['created', 'pending', 'assigned', 'in_progress']
    )
    
    context = {
        'orders_without_courier': orders_without_courier,
        'delayed_orders': delayed_orders,
    }
    return render(request, 'accounts/manager_tasks.html', context)


@login_required
def manager_orders(request):
    "Страница управления заказами"
    if request.user.role != 'manager':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('accounts:home')
    
    orders = Order.objects.all().order_by('-created_at')
    
    context = {
        'orders': orders,
    }
    return render(request, 'accounts/manager_orders.html', context)


@login_required
def manager_couriers(request):
    "Страница управления курьерами"
    if request.user.role != 'manager':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('accounts:home')
    
    couriers = Courier.objects.select_related('user').all()
    
    context = {
        'couriers': couriers,
    }
    return render(request, 'accounts/manager_couriers.html', context)


@login_required
def manager_clients(request):
    "Страница управления клиентами"
    if request.user.role != 'manager':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('accounts:home')
    
    clients = Client.objects.select_related('user').all()
    
    context = {
        'clients': clients,
    }
    return render(request, 'accounts/manager_clients.html', context)


@login_required
def manager_reports(request):
    "Страница отчетов"
    if request.user.role != 'manager':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('accounts:home')
    
    context = {}
    return render(request, 'accounts/manager_reports.html', context)


@login_required
def manager_settings(request):
    "Настройки менеджера"
    if request.user.role != 'manager':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('accounts:home')
    
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.phone = request.POST.get('phone')
        user.save()
        messages.success(request, 'Профиль успешно обновлен')
        return redirect('accounts:manager_settings')
    
    return render(request, 'accounts/manager_settings.html')

@login_required
def manager_tasks_count(request):
    """API для получения количества задач менеджера"""
    if request.user.role != 'manager':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    # Заказы без курьера (created или pending)
    orders_without_courier = Order.objects.filter(
        status__in=['created', 'pending']
    ).count()
    
    # Просроченные заказы
    from django.utils import timezone
    delayed_orders = Order.objects.filter(
        requested_delivery_date__lt=timezone.now().date(),
        status__in=['created', 'pending', 'assigned', 'in_progress']
    ).count()
    
    # Общее количество задач
    total_tasks = orders_without_courier + delayed_orders
    
    return JsonResponse({'count': total_tasks})