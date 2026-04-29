from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse  
from .forms import OrderForm
from .models import Order, Courier, OrderStatusHistory, CourierNotification, CourierShift, CourierShiftBreak, User, Campaign, CampaignRecipient
from django.utils import timezone
from datetime import timedelta
import json
from django.contrib.auth import update_session_auth_hash
from django.db.models import F 
from django.core.paginator import Paginator
from delivery.websocket_utils import send_order_status_update, send_notification_to_user, notify_order_assigned

@login_required
def create_order(request):
    try:
        client_profile = request.user.client_profile
    except:
        messages.error(request, 'Сначала заполните данные компании в настройках профиля')
        return redirect('accounts:company_setup')
    
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.client = client_profile
            order.order_type = request.POST.get('order_type', 'documents')
            order.status = 'created'
            order.save()
            
            OrderStatusHistory.objects.create(
                order=order,
                status='created',
                comment=f'Заказ создан клиентом {request.user.get_full_name()}'
            )
            
            messages.success(request, 'Заказ успешно создан!')
            return redirect('accounts:clients_orders')
    else:
        form = OrderForm()
    
    context = {
        'form': form,
        'active_tab': 'create_order',
    }
    
    return render(request, 'delivery/order_create.html', context) 

@login_required
def order_list(request):
    orders = Order.objects.filter(client=request.user.client_profile)
    return render(request, 'delivery/order_list.html', {'orders': orders})

@login_required
def order_detail(request, order_id):
    # Если пользователь курьер, перенаправляем на страницу курьера
    if request.user.role == 'courier':
        return redirect('delivery:courier_order_detail', order_id=order_id)
    
    # Если пользователь не клиент, показываем ошибку
    if not hasattr(request.user, 'client_profile'):
        messages.error(request, 'У вас нет доступа к этому заказу')
        return redirect('accounts:home')
    
    order = get_object_or_404(Order, id=order_id, client=request.user.client_profile)
    return render(request, 'delivery/order_detail.html', {'order': order})
    

@login_required
def assign_courier(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    if request.user.role != 'manager':
        messages.error(request, 'У вас нет прав для этого действия')
        return redirect('delivery:order_list')
    
    available_couriers = Courier.objects.filter(shift_status='on')
    
    if request.method == 'POST':
        courier_id = request.POST.get('courier')
        if courier_id:
            courier = get_object_or_404(Courier, id=courier_id)
            order.courier = courier
            order.status = 'pending'
            order.save()
            
            OrderStatusHistory.objects.create(
                order=order,
                status='assigned',
                comment=f'Назначен курьер {courier.user.get_full_name()}'
            )

            from delivery.websocket_utils import notify_order_assigned
            notify_order_assigned(order, courier.user.id)
            
            messages.success(request, 'Курьер назначен')
            return redirect('delivery:order_list')
    
    return render(request, 'delivery/assign_courier.html', {
        'order': order,
        'couriers': available_couriers
    })

@login_required
def delete_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, client=request.user.client_profile)
    
    if request.method == 'POST':
        order.delete()
        messages.success(request, 'Заказ удален')
        return redirect('delivery:order_list')
    
    return render(request, 'delivery/order_confirm_delete.html', {'order': order})


@login_required
def courier_reject_order(request, order_id):
    "Курьер отклоняет заказ"
    if request.user.role != 'courier':
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    
    try:
        order = get_object_or_404(Order, id=order_id, status='pending')
        courier = request.user.courier_profile
        
        # Создаем запись в истории, что курьер отклонил
        OrderStatusHistory.objects.create(
            order=order,
            status='pending',
            comment=f'Курьер {request.user.get_full_name()} отклонил заказ'
        )
        
        # Создаем уведомление (если модель есть, иначе пропускаем)
        try:
            CourierNotification.objects.create(
                courier=courier,
                order=order,
                message=f'Курьер {request.user.get_full_name()} отклонил заказ №{order.id}',
                notification_type='rejected'
            )
        except:
            pass  # Если модели нет, просто пропускаем
        
        return JsonResponse({'success': True, 'message': 'Заказ отклонен'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
@login_required
def complete_order(request, order_id):
    "Отметить заказ как доставленный"
    if request.user.role != 'courier' and request.user.role != 'manager':
        messages.error(request, 'У вас нет прав для этого действия')
        return redirect('delivery:order_list')
    
    order = get_object_or_404(Order, id=order_id)
    
    if order.status == 'in_progress':
        order.status = 'delivered'
        order.delivered_at = timezone.now()
        order.save()
        
        OrderStatusHistory.objects.create(
            order=order,
            status='delivered',
            comment=f'Заказ доставлен {request.user.get_full_name()}'
        )
        
        messages.success(request, f'Заказ №{order.id} отмечен как доставленный')
    else:
        messages.error(request, 'Заказ не может быть отмечен как доставленный (статус должен быть "В пути")')
    
    return redirect('delivery:order_list')

@login_required
def courier_dashboard(request):
    "Главная страница курьера"
    if request.user.role != 'courier':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('accounts:home')
    
    courier = request.user.courier_profile
    
    # Новые заказы (статус pending)
    new_orders = Order.objects.filter(
        status='pending',
        courier=courier  # Только заказы, назначенные на этого курьера
    ).order_by('-created_at')
    
    # Текущий статус смены
    shift_status = courier.shift_status
    
    # Текущая смена (незавершенная)
    current_shift = CourierShift.objects.filter(courier=courier, end_time__isnull=True).first()
    shift_start_time = current_shift.start_time if current_shift else None
    
    # Время перерыва
    current_break = None
    if current_shift:
        current_break = CourierShiftBreak.objects.filter(shift=current_shift, end_time__isnull=True).first()
    
    context = {
        'new_orders': new_orders,
        'shift_status': shift_status,
        'shift_start_time': shift_start_time,
        'current_break': current_break,
        'active_tab': 'dashboard',
    }
    return render(request, 'courier/courier_dashboard.html', context)


@login_required
def courier_update_shift(request):
    "Обновление статуса смена курьера"
    if request.user.role != 'courier':
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    
    courier = request.user.courier_profile  
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_status = data.get('status') 
        except:
            return JsonResponse({'error': 'Неверный JSON'}, status=400)
        
        # Начинаем смену
        if new_status == 'on' and courier.shift_status == 'off':
            courier.shift_status = 'on'
            courier.save()
            
            CourierShift.objects.create(
                courier=courier,
                start_time=timezone.now()
            )
            return JsonResponse({'success': True, 'status': 'on'})
        
        # Завершаем смену
        elif new_status == 'off' and courier.shift_status in ['on', 'break']:
            current_shift = CourierShift.objects.filter(
                courier=courier,
                end_time__isnull=True
            ).first()
            
            if current_shift:
                current_break = CourierShiftBreak.objects.filter(
                    shift=current_shift,
                    end_time__isnull=True
                ).first()
                
                if current_break:
                    current_break.end_break()
                
                current_shift.end_shift()
            
            courier.shift_status = 'off'
            courier.save()
            
            return JsonResponse({'success': True, 'status': 'off'})
        
        return JsonResponse({'error': 'Некорректный статус'}, status=400)
    
    return JsonResponse({'error': 'Метод не разрешен'}, status=405)


@login_required
def courier_start_break(request):
    "Начать перерыв"
    if request.user.role != 'courier':
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    
    if request.method == 'POST':
        courier = request.user.courier_profile
        
        if courier.shift_status != 'on':
            return JsonResponse({'error': 'Можно начать перерыв только во время смены'}, status=400)
        
        current_shift = CourierShift.objects.filter(courier=courier, end_time__isnull=True).first()
        
        if not current_shift:
            return JsonResponse({'error': 'Нет активной смены'}, status=400)
        
        # Проверяем, нет ли уже активного перерыва
        existing_break = CourierShiftBreak.objects.filter(shift=current_shift, end_time__isnull=True).first()
        if existing_break:
            return JsonResponse({'error': 'Перерыв уже активен'}, status=400)
        
        courier.shift_status = 'break'
        courier.save()
        
        CourierShiftBreak.objects.create(
            shift=current_shift,
            start_time=timezone.now()
        )
        
        return JsonResponse({'success': True, 'message': 'Перерыв начат', 'status': 'break'})
    
    return JsonResponse({'error': 'Метод не разрешен'}, status=405)


@login_required
def courier_end_break(request):
    "Завершить перерыв"
    if request.user.role != 'courier':
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    
    if request.method == 'POST':
        courier = request.user.courier_profile
        
        if courier.shift_status != 'break':
            return JsonResponse({'error': 'Нет активного перерыва'}, status=400)
        
        current_shift = CourierShift.objects.filter(courier=courier, end_time__isnull=True).first()
        
        if not current_shift:
            return JsonResponse({'error': 'Нет активной смены'}, status=400)
        
        current_break = CourierShiftBreak.objects.filter(shift=current_shift, end_time__isnull=True).first()
        
        if current_break:
            current_break.end_break()
        
        courier.shift_status = 'on'
        courier.save()
        
        return JsonResponse({'success': True, 'message': 'Перерыв завершен', 'status': 'on'})
    
    return JsonResponse({'error': 'Метод не разрешен'}, status=405)


@login_required
def courier_accept_order(request, order_id):
    "Курьер принимает заказ"
    if request.user.role != 'courier':
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    
    if request.method == 'POST':
        try:
            order = get_object_or_404(Order, id=order_id, status='pending')
            courier = request.user.courier_profile
            
            # Назначаем курьера
            order.courier = courier
            order.status = 'assigned'
            order.save()
            
            # Создаем запись в истории
            OrderStatusHistory.objects.create(
                order=order,
                status='assigned',
                comment=f'Курьер {request.user.get_full_name()} принял заказ'
            )
            
            return JsonResponse({'success': True, 'message': 'Заказ принят'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Метод не разрешен'}, status=405)


@login_required
def courier_reject_order(request, order_id):
    "Курьер отклоняет заказ"
    if request.user.role != 'courier':
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    
    if request.method == 'POST':
        try:
            courier = request.user.courier_profile

            order = get_object_or_404(
                Order,
                id=order_id,
                status='pending',
                courier=courier  
            )
            
            order.courier = None
            order.status = 'pending'
            order.save()
            
            OrderStatusHistory.objects.create(
                order=order,
                status='pending',
                comment=f'Курьер {request.user.get_full_name()} отклонил заказ'
            )
            
            return JsonResponse({'success': True, 'message': 'Заказ отклонен'})
        
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Метод не разрешен'}, status=405)

@login_required
def courier_active_orders(request):
    "Активные заказы курьера"
    if request.user.role != 'courier':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('accounts:home')
    
    courier = request.user.courier_profile
    active_orders = Order.objects.filter(
        courier=courier,
        status__in=['assigned', 'in_progress']
    ).order_by('-created_at')
    
    context = {
        'active_orders': active_orders,
        'active_tab': 'active_orders',
    }
    return render(request, 'courier/courier_active_orders.html', context)

@login_required
def courier_active_count(request):
    "Количество активных заказов для иконки"
    if request.user.role != 'courier':
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    
    courier = request.user.courier_profile
    count = Order.objects.filter(
        courier=courier,
        status__in=['assigned', 'in_progress']
    ).count()
    
    return JsonResponse({'count': count})

@login_required
def courier_order_detail(request, order_id):
    "Страница деталей заказа для курьера"
    if request.user.role != 'courier':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('accounts:home')
    
    courier = request.user.courier_profile
    order = get_object_or_404(Order, id=order_id, courier=courier)
    
    # Получаем историю статусов
    status_history = OrderStatusHistory.objects.filter(order=order).order_by('-changed_at')
    
    context = {
        'order': order,
        'status_history': status_history,
        'active_tab': 'active_orders',
    }
    return render(request, 'courier/courier_order_detail.html', context)

@login_required
def courier_update_order_status(request):
    "Курьер обновляет статус заказа"
    if request.user.role != 'courier':
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_id = data.get('order_id')
            new_status = data.get('status')
            
            courier = request.user.courier_profile
            order = get_object_or_404(Order, id=order_id, courier=courier)
            
            valid_transitions = {
                'assigned': ['in_progress'],
                'in_progress': ['delivered'],
            }
            
            if new_status not in valid_transitions.get(order.status, []):
                return JsonResponse({'error': 'Некорректный переход статуса'}, status=400)
            
            old_status = order.status
            order.status = new_status
            order.save()
            
            if new_status == 'delivered':
                order.delivered_at = timezone.now()
                order.save()
            
            status_display = dict(Order.STATUS_CHOICES).get(new_status, new_status)
            OrderStatusHistory.objects.create(
                order=order,
                status=new_status,
                comment=f'Курьер {request.user.get_full_name()} изменил статус на "{status_display}"'
            )
            
            # ОТПРАВКА WEBSOCKET УВЕДОМЛЕНИЙ
            from delivery.websocket_utils import send_order_status_update
            
            # Уведомляем менеджеров
            managers = User.objects.filter(role='manager')
            for manager in managers:
                send_order_status_update(
                    order_id=order.id,
                    user_id=manager.id,
                    status=new_status,
                    status_display=status_display,
                    courier_name=courier.user.get_full_name()
                )
            
            # Уведомляем клиента
            send_order_status_update(
                order_id=order.id,
                user_id=order.client.user.id,
                status=new_status,
                status_display=status_display,
                courier_name=courier.user.get_full_name()
            )
            
            # Уведомляем курьера
            send_order_status_update(
                order_id=order.id,
                user_id=request.user.id,
                status=new_status,
                status_display=status_display,
                courier_name=courier.user.get_full_name()
            )
            
            print(f"WebSocket уведомления отправлены для заказа #{order_id}")
            
            return JsonResponse({'success': True, 'message': 'Статус обновлен'})
            
        except Exception as e:
            print(f"Ошибка: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Метод не разрешен'}, status=405)
    
@login_required
def courier_order_readonly(request, order_id):
    "Страница просмотра заказа для курьера (только чтение)"
    if request.user.role != 'courier':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('accounts:home')
    
    courier = request.user.courier_profile
    order = get_object_or_404(Order, id=order_id, courier=courier)
    
    # Получаем историю статусов
    status_history = OrderStatusHistory.objects.filter(order=order).order_by('-changed_at')
    
    context = {
        'order': order,
        'status_history': status_history,
        'active_tab': 'dashboard',
    }
    return render(request, 'courier/courier_order_readonly.html', context)

# ЛК курьер настройки
@login_required
def courier_profile(request):
    "Профиль курьера - меню настроек"
    if request.user.role != 'courier':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('accounts:home')
    
    return render(request, 'courier/courier_profile.html', {'active_tab': 'profile'})


@login_required
def courier_settings_menu(request):
    "Меню настроек курьера"
    if request.user.role != 'courier':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('accounts:home')
    
    return render(request, 'courier/courier_settings_menu.html', {'active_tab': 'settings'})


@login_required
def courier_settings_profile(request):
    "Редактирование профиля курьера"
    if request.user.role != 'courier':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('accounts:home')
    
    if request.method == 'POST':
        user = request.user
        user.last_name = request.POST.get('last_name', '')
        user.first_name = request.POST.get('first_name', '')
        user.patronymic = request.POST.get('patronymic', '')
        user.phone = request.POST.get('phone', '')
        user.save()
        messages.success(request, 'Профиль успешно обновлен')
        return redirect('delivery:courier_settings_profile')
    
    return render(request, 'courier/courier_settings_profile.html', {'active_tab': 'profile'})


@login_required
def courier_settings_statistics(request):
    "Статистика курьера"
    if request.user.role != 'courier':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('accounts:home')
    
    courier = request.user.courier_profile
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    completed_orders = Order.objects.filter(
        courier=courier,
        status='delivered',
        delivered_at__gte=thirty_days_ago
    )
    
    completed_count = completed_orders.count()
    
    delivery_times = []
    for order in completed_orders:
        in_progress_history = OrderStatusHistory.objects.filter(
            order=order,
            status='in_progress'
        ).first()
        
        if in_progress_history and order.delivered_at:
            delivery_time = order.delivered_at - in_progress_history.changed_at
            delivery_times.append(delivery_time.total_seconds() / 60)
    
    avg_delivery_time = sum(delivery_times) / len(delivery_times) if delivery_times else 0
    
    late_orders = completed_orders.filter(
        delivered_at__date__gt=F('requested_delivery_date')
    ).count()
    
    context = {
        'stats': {
            'completed_orders': completed_count,
            'avg_delivery_time': round(avg_delivery_time, 1),
            'late_orders': late_orders,
            'avg_rating': float(courier.avg_rating) if courier.avg_rating else 0,
        },
        'thirty_days_ago': thirty_days_ago,
        'active_tab': 'profile',
    }
    
    return render(request, 'courier/courier_settings_statistics.html', context)

@login_required
def courier_settings_security(request):
    "Безопасность курьера (смена пароля)"
    if request.user.role != 'courier':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('accounts:home')
    
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not request.user.check_password(current_password):
            messages.error(request, 'Неверный текущий пароль')
        elif new_password != confirm_password:
            messages.error(request, 'Новый пароль и подтверждение не совпадают')
        elif len(new_password) < 8:
            messages.error(request, 'Пароль должен содержать минимум 8 символов')
        else:
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Пароль успешно изменен')
        return redirect('delivery:courier_settings_security')
    
    return render(request, 'courier/courier_settings_security.html', {'active_tab': 'profile'})

@login_required
def courier_settings_history(request):
    "История заказов курьера"
    if request.user.role != 'courier':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('accounts:home')
    
    courier = request.user.courier_profile
    
    completed_orders = Order.objects.filter(
        courier=courier,
        status='delivered'
    ).order_by('-delivered_at')
    
    # Пагинация
    paginator = Paginator(completed_orders, 4)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Добавляем время доставки для каждого заказа
    for order in page_obj:
        in_progress_history = OrderStatusHistory.objects.filter(
            order=order,
            status='in_progress'
        ).first()
        
        if in_progress_history and order.delivered_at:
            delivery_time = order.delivered_at - in_progress_history.changed_at
            order.delivery_time_minutes = int(delivery_time.total_seconds() / 60)
        else:
            order.delivery_time_minutes = '—'
    
    context = {
        'page_obj': page_obj,
        'active_tab': 'settings',
    }
    
    return render(request, 'courier/courier_settings_history.html', context)

@login_required
def courier_order_detail_page(request, order_id):
    "Страница деталей заказа для курьера"
    if request.user.role != 'courier':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('accounts:home')
    
    courier = request.user.courier_profile
    order = get_object_or_404(Order, id=order_id, courier=courier)
    
    # Получаем номер страницы из GET параметра
    page_number = request.GET.get('page', '1')
    
    # Получаем историю статусов
    status_history = OrderStatusHistory.objects.filter(order=order).order_by('-changed_at')
    
    context = {
        'order': order,
        'status_history': status_history,
        'page_number': page_number,
        'active_tab': 'settings',
    }
    return render(request, 'courier/courier_order_detail_page.html', context)

def courier_check_new_orders(request):
    "API проверки новых заказов для курьера"
    if request.user.role != 'courier':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    courier = request.user.courier_profile
    
    # Получаем все pending заказы для этого курьера
    new_orders = Order.objects.filter(
        status='pending',
        courier=courier
    ).values('id', 'pickup_address', 'delivery_address', 'weight', 'created_at')
    
    # Добавляем отображаемое название типа заказа
    order_list = []
    for order in new_orders:
        order_list.append({
            'id': order['id'],
            'pickup_address': order['pickup_address'],
            'delivery_address': order['delivery_address'],
            'weight': str(order['weight']) if order['weight'] else 'не указан',
            'created_at': order['created_at'].strftime('%d.%m %H:%M') if order['created_at'] else '',
            'order_type_display': dict(Order.ORDER_TYPE_CHOICES).get(order.get('order_type'), 'Документация')
        })
    
    return JsonResponse({'new_orders': order_list, 'has_new': len(order_list) > 0})

@login_required
def courier_update_shift_with_slot(request):
    "Обновление статуса смены курьера с указанием рабочего времени"
    if request.user.role != 'courier':
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    
    courier = request.user.courier_profile
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_status = data.get('status')
            work_slot = data.get('work_slot', 'full')
            custom_start = data.get('custom_start')
            custom_end = data.get('custom_end')
            
            print(f"DEBUG: new_status={new_status}, work_slot={work_slot}, custom_start={custom_start}, custom_end={custom_end}")
            
            if new_status == 'on' and courier.shift_status == 'off':
                # Проверяем, есть ли уже активная смена
                existing_shift = CourierShift.objects.filter(
                    courier=courier,
                    end_time__isnull=True
                ).first()
                
                if existing_shift:
                    return JsonResponse({'error': 'У вас уже есть активная смена'}, status=400)
                
                # Сохраняем выбранный слот
                courier.work_slot = work_slot
                if custom_start and custom_end:
                    courier.work_start_time = custom_start
                    courier.work_end_time = custom_end
                courier.shift_status = 'on'
                courier.save()
                
                # Создаем смену
                CourierShift.objects.create(
                    courier=courier,
                    start_time=timezone.now(),
                )
                
                return JsonResponse({'success': True, 'status': 'on'})
            else:
                return JsonResponse({'error': f'Некорректный статус: shift_status={courier.shift_status}, new_status={new_status}'}, status=400)
            
        except Exception as e:
            print(f"Ошибка: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Метод не разрешен'}, status=405)

@login_required
def create_campaign(request):
    "Создание массовой рассылки (кампании)"
    if request.method == 'POST':
        try:
            # Получаем данные кампании
            campaign_name = request.POST.get('campaign_name')
            occasion = request.POST.get('occasion')
            pickup_address = request.POST.get('campaign_pickup_address')
            campaign_comment = request.POST.get('campaign_comment', '')
            delivery_mode = request.POST.get('delivery_mode', 'one_day')
            delivery_date = request.POST.get('delivery_date')
            
            # Валидация
            if not campaign_name:
                messages.error(request, 'Введите название кампании')
                return redirect('delivery:create_order')
            
            if not pickup_address:
                messages.error(request, 'Введите адрес забора')
                return redirect('delivery:create_order')
            
            # Получаем списки получателей
            recipient_names = request.POST.getlist('recipient_full_name[]')
            recipient_phones = request.POST.getlist('recipient_phone[]')
            recipient_addresses = request.POST.getlist('recipient_address[]')
            recipient_companies = request.POST.getlist('recipient_company[]')
            recipient_comments = request.POST.getlist('recipient_comment[]')
            
            if not recipient_names or len(recipient_names) == 0:
                messages.error(request, 'Добавьте хотя бы одного получателя')
                return redirect('delivery:create_order')
            
            # Создаем кампанию
            campaign = Campaign.objects.create(
                client=request.user.client_profile,
                name=campaign_name,
                occasion=occasion,
                pickup_address=pickup_address,
                comment=campaign_comment,
                delivery_mode=delivery_mode,
                delivery_date=delivery_date if delivery_date else None,
            )
            
            # Создаем получателей и отдельные заказы
            for i in range(len(recipient_names)):
                if not recipient_names[i] or not recipient_phones[i] or not recipient_addresses[i]:
                    continue
                    
                # Разбираем ФИО
                name_parts = recipient_names[i].strip().split(' ', 2)
                last_name = name_parts[0] if len(name_parts) > 0 else ''
                first_name = name_parts[1] if len(name_parts) > 1 else ''
                patronymic = name_parts[2] if len(name_parts) > 2 else ''
                
                # Создаем отдельный заказ для каждого получателя
                order = Order.objects.create(
                    client=request.user.client_profile,
                    order_type='gifts',
                    pickup_address=pickup_address,
                    delivery_address=recipient_addresses[i],
                    recipient_last_name=last_name,
                    recipient_first_name=first_name,
                    recipient_patronymic=patronymic,
                    recipient_phone=recipient_phones[i],
                    recipient_company=recipient_companies[i] if i < len(recipient_companies) else '',
                    client_comment=recipient_comments[i] if i < len(recipient_comments) else campaign_comment,
                    requested_delivery_date=delivery_date or timezone.now().date(),
                    status='created'
                )
                
                # Создаем запись получателя в кампании
                CampaignRecipient.objects.create(
                    campaign=campaign,
                    company_name=recipient_companies[i] if i < len(recipient_companies) else '',
                    first_name=first_name,
                    last_name=last_name,
                    patronymic=patronymic,
                    phone=recipient_phones[i],
                    address=recipient_addresses[i],
                    comment=recipient_comments[i] if i < len(recipient_comments) else '',
                    order=order
                )
                
                # История статуса
                OrderStatusHistory.objects.create(
                    order=order,
                    status='created',
                    comment=f'Создан в рамках кампании "{campaign_name}"'
                )
            
            # Обновляем статистику кампании
            campaign.total_recipients = CampaignRecipient.objects.filter(campaign=campaign).count()
            campaign.save()
            
            messages.success(request, f'Кампания "{campaign_name}" успешно создана! Отправлено {campaign.total_recipients} получателей.')
            return redirect('accounts:clients_orders')
            
        except Exception as e:
            messages.error(request, f'Ошибка при создании кампании: {str(e)}')
            return redirect('delivery:create_order')
    
    return redirect('delivery:create_order')  
