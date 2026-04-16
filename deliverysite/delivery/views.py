from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse  
from .forms import OrderForm
from .models import Order, Courier, OrderStatusHistory, CourierNotification, CourierShift, CourierShiftBreak
from django.utils import timezone
from datetime import timedelta
import json

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
            order.status = 'assigned'
            order.save()
            
            OrderStatusHistory.objects.create(
                order=order,
                status='assigned',
                comment=f'Назначен курьер {courier.user.get_full_name()}'
            )
            
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
def courier_accept_order(request, order_id):
    "Курьер принимает заказ"
    if request.user.role != 'courier':
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    
    try:
        order = get_object_or_404(Order, id=order_id, status='pending', 
                                  courier=request.user.courier_profile)
        
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
def courier_profile(request):
    "Профиль курьера"
    if request.user.role != 'courier':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('accounts:home')
    
    courier = request.user.courier_profile
    
    total_deliveries = Order.objects.filter(courier=courier, status='delivered').count()
    rating = courier.avg_rating
    
    context = {
        'courier': courier,
        'total_deliveries': total_deliveries,
        'rating': rating,
        'active_tab': 'profile',
    }
    return render(request, 'courier/courier_profile.html', context)


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