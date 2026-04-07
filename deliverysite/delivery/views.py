from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from .forms import OrderForm
from delivery.models import Order, Courier, OrderStatusHistory, Client
from django.contrib.auth.decorators import login_required

# CREATE: Создание заказа
@login_required
def create_order(request):
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            # Получаем профиль клиента текущего пользователя
            try:
                client_profile = request.user.client_profile
                order.client = client_profile
            except Client.DoesNotExist:
                messages.error(request, 'У вас нет профиля клиента. Обратитесь к менеджеру.')
                return redirect('home')
            
            order.save()

            # создаем первый статус в истории
            OrderStatusHistory.objects.create(
                order=order,
                status='created',
                comment='Заказ создан клиентом'
            )

            messages.success(
                request,
                'Ваш заказ создан. В ближайшее время с вами свяжется менеджер.'
            )

            return redirect('order_list')  # редирект на список заказов
    else:
        form = OrderForm()

    return render(request, 'delivery/order_create.html', {'form': form})


# READ: просмотр всех созданных заказов
@login_required
def order_list(request):
    # Показываем только заказы текущего клиента
    try:
        client_profile = request.user.client_profile
        orders = Order.objects.filter(client=client_profile).select_related('courier')
    except Client.DoesNotExist:
        orders = Order.objects.none()
        messages.info(request, 'У вас нет профиля клиента')
    
    return render(request, 'delivery/order_list.html', {'orders': orders})


# UPDATE: назначение курьера (только для менеджеров)
@login_required
def assign_courier(request, order_id):
    # Проверка, что пользователь - менеджер
    if request.user.role != 'manager':
        messages.error(request, 'У вас нет прав для этого действия')
        return redirect('order_list')
    
    order = get_object_or_404(Order, id=order_id)

    available_couriers = [
        courier for courier in Courier.objects.all()
        if courier.is_available()
    ]

    if request.method == 'POST':
        courier_id = request.POST.get('courier')
        if courier_id:
            courier = get_object_or_404(Courier, id=courier_id)

            order.courier = courier
            order.status = 'assigned'
            order.save()

            # создаем новый статус в истории
            OrderStatusHistory.objects.create(
                order=order,
                status='assigned',
                comment=f'Назначен курьер: {courier.user.get_full_name()}'
            )

            messages.success(request, 'Курьер назначен')
            return redirect('order_list')

    return render(
        request,
        'delivery/assign_courier.html',
        {
            'order': order,
            'couriers': available_couriers
        }
    )


# DELETE: удаление заказа (только для клиента, чей это заказ)
@login_required
def delete_order(request, order_id):
    try:
        client_profile = request.user.client_profile
        order = get_object_or_404(Order, id=order_id, client=client_profile)
    except Client.DoesNotExist:
        messages.error(request, 'У вас нет профиля клиента')
        return redirect('order_list')

    if request.method == 'POST':
        order.delete()
        messages.success(request, 'Заказ успешно удалён')
        return redirect('order_list')

    return render(request, 'delivery/order_confirm_delete.html', {
        'order': order
    })