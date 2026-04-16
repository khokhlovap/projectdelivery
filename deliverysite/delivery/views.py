from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse  
from .forms import OrderForm
from .models import Order, Courier, OrderStatusHistory, CourierNotification
from django.utils import timezone

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
    """Курьер отклоняет заказ"""
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