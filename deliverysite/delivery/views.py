from django.contrib import messages
from django.shortcuts import render
from .forms import OrderForm

# CREATE: Создание заказа
def create_order(request):
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.client = request.user   # автоматически текущий пользователь
            order.save()
            messages.success(
                request,
                'Ваш заказ создан. В ближайшее время с вами свяжется менеджер.'
            )

            return render(request, 'delivery/order_create.html', {
                'form': OrderForm()
            })
    else:
        form = OrderForm()
    return render(request, 'delivery/order_create.html', {'form': form})