from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from .forms import OrderForm
from delivery.models import Order, Courier, OrderStatus

# CREATE: Создание заказа
def create_order(request):
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.client = request.user
            order.save()

            # создаем первый статус
            OrderStatus.objects.create(
                order=order,
                status='created'
            )

            messages.success(
                request,
                'Ваш заказ создан. В ближайшее время с вами свяжется менеджер.'
            )

            return render(
                request,
                'delivery/order_create.html',
                {'form': OrderForm()}
            )
    else:
        form = OrderForm()

    return render(request, 'delivery/order_create.html', {'form': form})


# READ: просмотр всех созланных заказов
def order_list(request):
    orders = Order.objects.select_related('client', 'courier', 'order_type')
    return render(request, 'delivery/order_list.html', {'orders': orders})

# UPDATE
def assign_courier(request, order_id):
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
            order.save()

            # создаем новый статус
            OrderStatus.objects.create(
                order=order,
                status='assigned'
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


# DELETE
def delete_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if request.method == 'POST':
        order.delete()
        messages.success(request, 'Заказ успешно удалён')
        return redirect('order_list')

    return render(request, 'delivery/order_confirm_delete.html', {
        'order': order
    })
