from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import RegistrationForm
from django.contrib.auth.forms import AuthenticationForm
from delivery.models import Order, Client

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
            
            try:
                if user.client_profile:
                    messages.success(request, f'Добро пожаловать, {user.get_full_name()}!')
                    return redirect('accounts:home')
            except:
                messages.warning(request, 'Пожалуйста, заполните данные компании')
                return redirect('accounts:company_setup')
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