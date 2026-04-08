from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import OrderForm
from .models import Order, Courier, OrderStatusHistory

@login_required
def create_order(request):
    # Проверяем, есть ли профиль клиента
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
            order.save()
            
            OrderStatusHistory.objects.create(
                order=order,
                status='created',
                comment='Заказ создан клиентом'
            )
            
            messages.success(request, 'Заказ успешно создан!')
            return redirect('accounts:orders')
    else:
        form = OrderForm()
    
    return render(request, 'delivery/order_create.html', {'form': form})
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
    
    available_couriers = [c for c in Courier.objects.all() if c.is_available()]
    
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