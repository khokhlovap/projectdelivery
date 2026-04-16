import json
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse  
from django.utils import timezone  
from .forms import RegistrationForm
from django.contrib.auth.forms import AuthenticationForm
from delivery.models import Order, Client, Courier, OrderRating, OrderStatusHistory, User 
from django.db.models import Count, Avg, Q
from datetime import datetime, timedelta
from django.core.paginator import Paginator
from django.contrib.auth.hashers import make_password
import random
import string
from django.db.models import Sum
from django.core.mail import send_mail
from django.conf import settings

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
        'active_tab': 'home',
    }
    return render(request, 'accounts/dashboard.html', context)

@login_required
def client_orders(request):
    "Все заказы клиента"
    try:
        client_profile = request.user.client_profile
        orders = Order.objects.filter(client=client_profile).order_by('-created_at')
        
        active_count = orders.filter(status__in=['created', 'pending', 'assigned', 'in_progress']).count()
        delivered_count = orders.filter(status='delivered').count()
        total_orders = orders.count()
        
        for order in orders:
            try:
                order.has_rating = hasattr(order, 'rating')
            except:
                order.has_rating = False
        
        paginator = Paginator(orders, 4)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
    except:
        page_obj = []
        active_count = 0
        delivered_count = 0
        total_orders = 0
    
    context = {
        'page_obj': page_obj,
        'active_count': active_count,
        'delivered_count': delivered_count,
        'total_orders': total_orders,
        'total_count': orders.count() if 'orders' in locals() else 0,
        'active_tab': 'orders',
    }
    return render(request, 'accounts/clients_orders.html', context)

@login_required
def rate_order(request):
    "Оценка заказа клиентом"
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не разрешен'}, status=405)
    
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        rating = data.get('rating')
        
        if not rating or rating < 1 or rating > 5:
            return JsonResponse({'error': 'Некорректная оценка'}, status=400)
        
        order = Order.objects.get(id=order_id, client=request.user.client_profile)
        
        # Проверка, есть ли уже оценка
        if hasattr(order, 'rating'):
            return JsonResponse({'error': 'Оценка уже была оставлена'}, status=400)
        
        # Проверка, что заказ доставлен
        if order.status != 'delivered':
            return JsonResponse({'error': 'Оценку можно оставить только после доставки'}, status=400)
        
        # Создаем оценку
        OrderRating.objects.create(
            order=order,
            client=request.user.client_profile,
            courier=order.courier,
            rating=rating
        )
        
        return JsonResponse({'success': True, 'message': 'Спасибо за оценку!'})
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Заказ не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
@login_required
def check_order_rating(request):
    "Проверка, есть ли уже оценка у заказа"
    order_id = request.GET.get('order_id')
    
    try:
        order = Order.objects.get(id=order_id, client=request.user.client_profile)
        has_rating = hasattr(order, 'rating')
        return JsonResponse({'has_rating': has_rating})
    except Order.DoesNotExist:
        return JsonResponse({'has_rating': True, 'error': 'Заказ не найден'}, status=404)
    
@login_required
def client_settings(request):
    "Настройки профиля клиента"
    try:
        client = request.user.client_profile
    except:
        client = None
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Обновление личных данных
        if action == 'update_profile':
            user = request.user
            user.first_name = request.POST.get('first_name', '').strip()
            user.last_name = request.POST.get('last_name', '').strip()
            user.patronymic = request.POST.get('patronymic', '').strip()
            user.phone = request.POST.get('phone', '').strip()
            user.save()
            messages.success(request, 'Личные данные успешно обновлены')
            return redirect('accounts:client_settings')
        
        # Обновление данных компании
        elif action == 'update_company':
            if client:
                client.company_name = request.POST.get('company_name', '').strip()
                client.inn = request.POST.get('inn', '').strip()
                client.kpp = request.POST.get('kpp', '').strip()
                client.legal_address = request.POST.get('legal_address', '').strip()
                client.actual_address = request.POST.get('actual_address', '').strip()
                client.company_phone = request.POST.get('company_phone', '').strip()
                client.company_email = request.POST.get('company_email', '').strip()
                client.bank = request.POST.get('bank', '').strip()
                client.settlement_account = request.POST.get('settlement_account', '').strip()
                client.correspondent_account = request.POST.get('correspondent_account', '').strip()
                client.contact_person_first_name = request.POST.get('contact_person_first_name', '').strip()
                client.contact_person_last_name = request.POST.get('contact_person_last_name', '').strip()
                client.contact_person_patronymic = request.POST.get('contact_person_patronymic', '').strip()
                client.contact_person_phone = request.POST.get('contact_person_phone', '').strip()
                client.contact_person_email = request.POST.get('contact_person_email', '').strip()
                client.save()
                messages.success(request, 'Данные компании успешно обновлены')
            else:
                messages.error(request, 'Профиль компании не найден')
            return redirect('accounts:client_settings')
        
        # Смена пароля
        elif action == 'change_password':
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if not request.user.check_password(current_password):
                messages.error(request, 'Текущий пароль введен неверно')
                return redirect('accounts:client_settings')
            
            if not new_password:
                messages.error(request, 'Введите новый пароль')
                return redirect('accounts:client_settings')
            
            if new_password != confirm_password:
                messages.error(request, 'Новый пароль и подтверждение не совпадают')
                return redirect('accounts:client_settings')
            
            if len(new_password) < 8:
                messages.error(request, 'Пароль должен содержать минимум 8 символов')
                return redirect('accounts:client_settings')
            
            request.user.set_password(new_password)
            request.user.save()
            
            messages.success(request, 'Пароль успешно изменен. Пожалуйста, войдите снова.')
            return redirect('accounts:login')
    
    context = {
        'user': request.user,
        'client': client,
        'active_tab': 'settings',
    }
    return render(request, 'accounts/client_settings.html', context)

@login_required
def ai_assistant(request):
    "AI помощник"
    context = {
    'active_tab': 'ai_assistant', 
    }
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
    if request.user.role != 'manager':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('accounts:home')
    
    orders = Order.objects.exclude(
        status__in=['delivered', 'cancelled']
    ).order_by('-created_at')
    
    # Добавляем информацию о последнем статусе
    for order in orders:
        last_status = OrderStatusHistory.objects.filter(order=order).order_by('-changed_at').first()
        order.last_status_text = last_status.get_status_display() if last_status else order.get_status_display()
        order.last_status_time = last_status.changed_at if last_status else order.created_at

    available_couriers = Courier.objects.filter(shift_status='on')
    
    # Отладка - вывод в консоль
    print(f"DEBUG: Найдено доступных курьеров: {len(available_couriers)}")
    for c in available_couriers:
        print(f"  - {c.user.get_full_name()}")
    
    context = {
        'orders': orders,
        'available_couriers': available_couriers,
    }
    return render(request, 'accounts/manager_tasks.html', context)


@login_required
def manager_orders(request):
    "Страница завершенных заказов"
    if request.user.role != 'manager':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('accounts:home')
    
    # Базовый запрос - только завершенные заказы (доставленные)
    orders = Order.objects.filter(status='delivered').order_by('-delivered_at', '-created_at')
    
    # Поиск по названию компании клиента
    search_query = request.GET.get('search', '')
    if search_query:
        orders = orders.filter(
            Q(client__company_name__icontains=search_query) |
            Q(client__contact_person_last_name__icontains=search_query) |
            Q(recipient_last_name__icontains=search_query) |
            Q(recipient_company__icontains=search_query)
        )
    
    # Фильтр по дате доставки
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Фильтр дат отдельно от поиска
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            orders = orders.filter(delivered_at__date__gte=date_from_obj)
        except (ValueError, TypeError):
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            orders = orders.filter(delivered_at__date__lte=date_to_obj)
        except (ValueError, TypeError):
            pass
    
    # Пагинация
    paginator = Paginator(orders, 4)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'total_count': orders.count(),
    }
    return render(request, 'accounts/manager_orders.html', context)


@login_required
def manager_couriers(request):
    "Страница управления курьерами"
    if request.user.role != 'manager':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('accounts:home')
    
    couriers = Courier.objects.select_related('user').all().order_by('-user__date_joined')
    
    # Поиск по ФИО
    search_query = request.GET.get('search', '')
    if search_query:
        couriers = couriers.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    
    # Пагинация
    paginator = Paginator(couriers, 4)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'total_count': couriers.count(),
    }
    return render(request, 'accounts/manager_couriers.html', context)

@login_required
def manager_courier_add(request):
    "Добавление нового курьера менеджером"
    if request.user.role != 'manager':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('accounts:home')
    
    if request.method == 'POST':
        # Генерируем временный пароль
        temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        
        # Создаем пользователя
        user = User.objects.create(
            email=email,
            first_name=first_name,
            last_name=last_name,
            patronymic=request.POST.get('patronymic', ''),
            phone=request.POST.get('phone'),
            role='courier',
            password=make_password(temp_password)
        )
        
        # Создаем профиль курьера
        from django.utils import timezone
        Courier.objects.create(
            user=user,
            hire_date=request.POST.get('hire_date') or timezone.now().date(),
            position=request.POST.get('position', 'Курьер'),
            shift_status=request.POST.get('shift_status', 'off'),
            citizenship=request.POST.get('citizenship'),
            passport_series=request.POST.get('passport_series'),
            passport_number=request.POST.get('passport_number'),
            passport_department_code=request.POST.get('passport_department_code'),
            passport_issued_by=request.POST.get('passport_issued_by'),
            passport_issue_date=request.POST.get('passport_issue_date'),
            registration_address=request.POST.get('registration_address'),
            actual_address=request.POST.get('actual_address'),
        )
        
        # Отправляем email с паролем
        try:
            send_mail(
                subject='Добро пожаловать в АВН Бизнес Курьер!',
                message=f"""
            Здравствуйте, {first_name} {last_name}!

            Вы были добавлены в систему АВН Бизнес Курьер в качестве курьера.

            Ваши данные для входа:
            Email: {email}
            Временный пароль: {temp_password}

            Пожалуйста, войдите в систему и смените пароль при первом входе.

            Ссылка для входа: http://127.0.0.1:8000/login/

            С уважением,
            Команда АВН Бизнес Курьер
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            messages.success(request, f'Курьер {email} успешно создан. Пароль отправлен на почту.')
        except Exception as e:
            messages.warning(request, f'Курьер создан, но не удалось отправить email: {e}. Временный пароль: {temp_password}')
        
        return redirect('accounts:manager_couriers')
    
    context = {
        'title': 'Добавить курьера',
        'courier_user': None,
        'courier': None,
    }
    return render(request, 'accounts/manager_courier_form.html', context)

@login_required
def manager_courier_edit(request, user_id):
    "Редактирование курьера"
    if request.user.role != 'manager':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('accounts:home')
    
    try:
        user = User.objects.get(id=user_id, role='courier')
        courier = user.courier_profile
    except (User.DoesNotExist, Courier.DoesNotExist):
        messages.error(request, 'Курьер не найден')
        return redirect('accounts:manager_couriers')
    
    if request.method == 'POST':
        # Обновляем пользователя
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.patronymic = request.POST.get('patronymic', '')
        user.phone = request.POST.get('phone')
        user.save()
        
        # Обновляем курьера
        courier.hire_date = request.POST.get('hire_date')
        courier.position = request.POST.get('position')
        courier.shift_status = request.POST.get('shift_status')
        courier.citizenship = request.POST.get('citizenship')
        courier.passport_series = request.POST.get('passport_series')
        courier.passport_number = request.POST.get('passport_number')
        courier.passport_department_code = request.POST.get('passport_department_code')
        courier.passport_issued_by = request.POST.get('passport_issued_by')
        courier.passport_issue_date = request.POST.get('passport_issue_date')
        courier.registration_address = request.POST.get('registration_address')
        courier.actual_address = request.POST.get('actual_address')
        courier.save()
        
        messages.success(request, 'Данные курьера обновлены')
        return redirect('accounts:manager_couriers')
    
    context = {
        'title': 'Редактировать курьера',
        'courier_user': user, 
        'courier': courier,
    }
    return render(request, 'accounts/manager_courier_form.html', context)

@login_required
def manager_courier_edit(request, user_id):
    "Редактирование курьера"
    if request.user.role != 'manager':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('accounts:home')
    
    try:
        user = User.objects.get(id=user_id, role='courier')
        courier = user.courier_profile
    except (User.DoesNotExist, Courier.DoesNotExist):
        messages.error(request, 'Курьер не найден')
        return redirect('accounts:manager_couriers')
    
    if request.method == 'POST':
        # Обновляем пользователя
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.patronymic = request.POST.get('patronymic', '')
        user.phone = request.POST.get('phone')
        user.save()
        
        # Обновляем курьера
        courier.hire_date = request.POST.get('hire_date')
        courier.position = request.POST.get('position')
        courier.shift_status = request.POST.get('shift_status')
        courier.citizenship = request.POST.get('citizenship')
        courier.passport_series = request.POST.get('passport_series')
        courier.passport_number = request.POST.get('passport_number')
        courier.passport_department_code = request.POST.get('passport_department_code')
        courier.passport_issued_by = request.POST.get('passport_issued_by')
        courier.passport_issue_date = request.POST.get('passport_issue_date')
        courier.registration_address = request.POST.get('registration_address')
        courier.actual_address = request.POST.get('actual_address')
        courier.save()
        
        messages.success(request, 'Данные курьера обновлены')
        return redirect('accounts:manager_couriers')
    
    context = {
        'title': 'Редактировать курьера',
        'courier_user': user,  
        'courier': courier,
    }
    return render(request, 'accounts/manager_courier_form.html', context)

@login_required
def manager_courier_detail(request, user_id):
    "Получение деталей курьера - модальное окно"
    if request.user.role != 'manager':
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    
    try:
        user = User.objects.get(id=user_id, role='courier')
        courier = user.courier_profile
        
        data = {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'patronymic': user.patronymic or '',
            'phone': user.phone or '',
            'date_joined': user.date_joined.strftime('%d.%m.%Y %H:%M'),
            'hire_date': courier.hire_date.strftime('%d.%m.%Y'),
            'position': courier.position,
            'shift_status': courier.get_shift_status_display(),
            'citizenship': courier.citizenship,
            'passport_series': courier.passport_series,
            'passport_number': courier.passport_number,
            'passport_department_code': courier.passport_department_code,
            'passport_issued_by': courier.passport_issued_by,
            'passport_issue_date': courier.passport_issue_date.strftime('%d.%m.%Y'),
            'registration_address': courier.registration_address,
            'actual_address': courier.actual_address,
            'total_orders': courier.total_orders,
            'avg_rating': float(courier.avg_rating),
            'total_work_hours': float(courier.total_work_hours),
        }
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=404)

@login_required
def manager_clients(request):
    "Страница управления клиентами"
    if request.user.role != 'manager':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('accounts:home')
    
    clients = Client.objects.select_related('user').annotate(
        orders_count=Count('orders')).order_by('-user__date_joined')
    
    # Поиск
    search_query = request.GET.get('search', '')
    if search_query:
        clients = clients.filter(
            Q(company_name__icontains=search_query) |
            Q(inn__icontains=search_query) |
            Q(contact_person_last_name__icontains=search_query) |
            Q(contact_person_first_name__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    
    # Пагинация
    paginator = Paginator(clients, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Дополнительная статистика
    from django.utils import timezone
    total_orders_count = Order.objects.filter(status='delivered').count()
    new_clients_this_month = Client.objects.filter(
        user__date_joined__month=timezone.now().month
    ).count()
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'total_count': clients.count(),
        'total_orders_count': total_orders_count,
        'new_clients_this_month': new_clients_this_month,
    }
    return render(request, 'accounts/manager_clients.html', context)

@login_required
def manager_client_add(request):
    "Добавление нового клиента менеджером"
    if request.user.role != 'manager':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('accounts:home')
    
    if request.method == 'POST':
        # Генеррация временного пароля
        temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        
        # Создаем пользователя
        user = User.objects.create(
            email=email,
            first_name=first_name,
            last_name=last_name,
            patronymic=request.POST.get('patronymic', ''),
            phone=request.POST.get('phone'),
            role='client',
            password=make_password(temp_password)
        )
        
        # Создаем профиль клиента
        Client.objects.create(
            user=user,
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
            contact_person_first_name=request.POST.get('contact_person_first_name'),
            contact_person_last_name=request.POST.get('contact_person_last_name'),
            contact_person_patronymic=request.POST.get('contact_person_patronymic', ''),
            contact_person_phone=request.POST.get('contact_person_phone'),
            contact_person_email=request.POST.get('contact_person_email'),
        )
        
        # Отправка письма (email) с паролем
        try:
            send_mail(
                subject='Добро пожаловать в АВН Бизнес Курьер!',
                message=f"""
                Здравствуйте, {first_name} {last_name}!

                Для вас был создан аккаунт в системе АВН Бизнес Курьер.

                Ваши данные для входа:
                Email: {email}
                Временный пароль: {temp_password}

                Пожалуйста, войдите в систему и смените пароль при первом входе.

                Ссылка для входа: http://127.0.0.1:8000/login/

                С уважением,
                Команда АВН Бизнес Курьер
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            messages.success(request, f'Клиент {email} успешно создан. Пароль отправлен на почту.')
        except Exception as e:
            messages.warning(request, f'Клиент создан, но не удалось отправить email: {e}. Временный пароль: {temp_password}')
        
        return redirect('accounts:manager_clients')
    
    context = {
        'title': 'Добавить клиента',
        'client_user': None,
        'client': None,
    }
    return render(request, 'accounts/manager_client_form.html', context)


@login_required
def manager_client_edit(request, user_id):
    "Редактирование клиента"
    if request.user.role != 'manager':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('accounts:home')
    
    try:
        user = User.objects.get(id=user_id, role='client')
        client = user.client_profile
    except (User.DoesNotExist, Client.DoesNotExist):
        messages.error(request, 'Клиент не найден')
        return redirect('accounts:manager_clients')
    
    if request.method == 'POST':
        # Обновлени пользователя
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.patronymic = request.POST.get('patronymic', '')
        user.phone = request.POST.get('phone')
        user.save()
        
        # Обновление клиента
        client.company_name = request.POST.get('company_name')
        client.inn = request.POST.get('inn')
        client.kpp = request.POST.get('kpp')
        client.legal_address = request.POST.get('legal_address')
        client.actual_address = request.POST.get('actual_address')
        client.company_phone = request.POST.get('company_phone')
        client.company_email = request.POST.get('company_email')
        client.bank = request.POST.get('bank')
        client.settlement_account = request.POST.get('settlement_account')
        client.correspondent_account = request.POST.get('correspondent_account')
        client.contact_person_first_name = request.POST.get('contact_person_first_name')
        client.contact_person_last_name = request.POST.get('contact_person_last_name')
        client.contact_person_patronymic = request.POST.get('contact_person_patronymic', '')
        client.contact_person_phone = request.POST.get('contact_person_phone')
        client.contact_person_email = request.POST.get('contact_person_email')
        client.save()
        
        messages.success(request, 'Данные клиента обновлены')
        return redirect('accounts:manager_clients')
    
    context = {
        'title': 'Редактировать клиента',
        'client_user': user,
        'client': client,
    }
    return render(request, 'accounts/manager_client_form.html', context)


@login_required
def manager_client_detail(request, user_id):
    "Получение деталей клиента для модального окна"
    if request.user.role != 'manager':
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    
    try:
        user = User.objects.get(id=user_id, role='client')
        client = user.client_profile
        orders_count = Order.objects.filter(client=client).count()
        
        data = {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'patronymic': user.patronymic or '',
            'phone': user.phone or '',
            'date_joined': user.date_joined.strftime('%d.%m.%Y %H:%M'),
            'company_name': client.company_name,
            'inn': client.inn,
            'kpp': client.kpp,
            'legal_address': client.legal_address,
            'actual_address': client.actual_address,
            'company_phone': client.company_phone,
            'company_email': client.company_email,
            'bank': client.bank,
            'settlement_account': client.settlement_account,
            'correspondent_account': client.correspondent_account,
            'contact_person_first_name': client.contact_person_first_name,
            'contact_person_last_name': client.contact_person_last_name,
            'contact_person_patronymic': client.contact_person_patronymic or '',
            'contact_person_phone': client.contact_person_phone,
            'contact_person_email': client.contact_person_email,
            'orders_count': orders_count,
        }
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=404)

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
    "Настройки менеджера - изменение профиля и пароля"
    if request.user.role != 'manager':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('accounts:home')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Обновление профиля
        if action == 'update_profile':
            user = request.user
            user.first_name = request.POST.get('first_name', '').strip()
            user.last_name = request.POST.get('last_name', '').strip()
            user.patronymic = request.POST.get('patronymic', '').strip()
            user.phone = request.POST.get('phone', '').strip()
            user.save()
            
            messages.success(request, 'Данные профиля успешно обновлены')
            return redirect('accounts:manager_settings')
        
        # Смена пароля
        elif action == 'change_password':
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            # Проверяем текущий пароль
            if not request.user.check_password(current_password):
                messages.error(request, 'Текущий пароль введен неверно')
                return redirect('accounts:manager_settings')
            
            # Проверяем, что новый пароль не пустой
            if not new_password:
                messages.error(request, 'Введите новый пароль')
                return redirect('accounts:manager_settings')
            
            # Проверяем совпадение паролей
            if new_password != confirm_password:
                messages.error(request, 'Новый пароль и подтверждение не совпадают')
                return redirect('accounts:manager_settings')
            
            # Проверяем длину пароля
            if len(new_password) < 8:
                messages.error(request, 'Пароль должен содержать минимум 8 символов')
                return redirect('accounts:manager_settings')
            
            # Меняем пароль
            request.user.set_password(new_password)
            request.user.save()
            
            messages.success(request, 'Пароль успешно изменен. Пожалуйста, войдите снова.')
            return redirect('accounts:login')
    
    context = {
        'user': request.user,
    }
    return render(request, 'accounts/manager_settings.html', context)

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

@login_required
def assign_courier_ajax(request):
    "AJAX назначение курьера на заказ"
    if request.user.role != 'manager':
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_id = data.get('order_id')
            user_id = data.get('courier_id')
            
            print(f"DEBUG: order_id={order_id}, user_id={user_id}")
            
            if not order_id or not user_id:
                return JsonResponse({'error': 'Не указаны ID заказа или курьера'}, status=400)
            
            order = Order.objects.get(pk=order_id)
            # Ищем курьера по user_id
            courier = Courier.objects.get(user_id=user_id)
            
            # Обновляем заказ
            order.courier = courier
            order.status = 'assigned'
            order.save()

            return JsonResponse({'success': True, 'message': 'Курьер успешно назначен'})
            
        except Order.DoesNotExist:
            return JsonResponse({'error': f'Заказ с ID {order_id} не найден'}, status=404)
        except Courier.DoesNotExist:
            return JsonResponse({'error': f'Курьер с ID {user_id} не найден'}, status=404)
        except Exception as e:
            print(f"DEBUG: Ошибка: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Метод не разрешен'}, status=405)
  
@login_required
def delete_order_ajax(request):
    "AJAX удаление заказа"
    if request.user.role != 'manager':
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        order_id = data.get('order_id')
        
        try:
            order = Order.objects.get(id=order_id)
            order.delete()
            return JsonResponse({'success': True, 'message': 'Заказ удален'})
        except Order.DoesNotExist:
            return JsonResponse({'error': 'Заказ не найден'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Метод не разрешен'}, status=405)

@login_required
def get_order_details(request):
    "Получение деталей заказа для модального окна"
    # Разрешаем доступ и менеджеру, и клиенту (владельцу заказа)
    
    order_id = request.GET.get('order_id')
    
    try:
        order = Order.objects.get(id=order_id)
        
        # Проверка прав доступа:
        # - Менеджер может смотреть любой заказ
        # - Клиент может смотреть только свои заказы
        if request.user.role == 'manager':
            pass  # менеджеру всё можно
        elif request.user.role == 'client':
            # Проверяем, что заказ принадлежит этому клиенту
            if order.client != request.user.client_profile:
                return JsonResponse({'error': 'Доступ запрещен'}, status=403)
        else:
            return JsonResponse({'error': 'Доступ запрещен'}, status=403)
        
        # Получаем всю историю статусов в хронологическом порядке
        status_history = OrderStatusHistory.objects.filter(order=order).order_by('changed_at')
        history_list = []
        for status in status_history:
            history_list.append({
                'status': status.get_status_display(),
                'time': status.changed_at.strftime('%d.%m.%Y %H:%M'),
                'comment': status.comment
            })
        
        # Получаем последний статус
        last_status = status_history.last()
        
        # Определяем статус оплаты из поля payment_status
        payment_status_display = dict(Order.PAYMENT_CHOICES).get(order.payment_status, 'Не указан')
        
        # Данные для клиента
        data = {
            'id': order.id,
            'client_name': order.client.company_name,
            'contact_person': order.client.get_contact_person_full_name(),
            'contact_phone': order.client.contact_person_phone,
            'pickup_address': order.pickup_address,
            'delivery_address': order.delivery_address,
            'order_type': order.get_order_type_display(),
            'tariff': order.get_tariff_display(),
            'weight': str(order.weight) if order.weight else 'не указан',
            'recipient_name': order.get_recipient_full_name(),
            'recipient_phone': order.recipient_phone,
            'recipient_company': order.recipient_company or '—',
            'created_at': order.created_at.strftime('%d.%m.%Y %H:%M'),
            'current_status': order.get_status_display(),
            'payment_status': payment_status_display, 
            'total_amount': str(order.total_amount) if order.total_amount else '0',
            'status_history': history_list,
            'client_comment': order.client_comment or 'Нет комментария',
        }
        
        # Добавляем информацию о курьере, если есть
        if order.courier:
            data['courier_name'] = order.courier.user.get_full_name()
            data['courier_phone'] = order.courier.user.phone or '—'
        else:
            data['courier_name'] = 'Не назначен'
            data['courier_phone'] = '—'
        
        return JsonResponse({'success': True, 'data': data})
        
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Заказ не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)