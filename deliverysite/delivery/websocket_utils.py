from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone

def send_order_status_update(order_id, user_id, status, status_display, courier_name=None):
    "Отправка обновления статуса заказа через WebSocket"
    channel_layer = get_channel_layer()
    
    async_to_sync(channel_layer.group_send)(
        f'orders_{user_id}',
        {
            'type': 'order_status_update',
            'order_id': order_id,
            'status': status,
            'status_display': status_display,
            'updated_at': str(timezone.now()),
            'courier_name': courier_name or ''
        }
    )

def send_notification_to_user(user_id, title, message, notification_type='info'):
    "Отправка уведомления пользователю"
    channel_layer = get_channel_layer()
    
    async_to_sync(channel_layer.group_send)(
        f'orders_{user_id}',
        {
            'type': 'notification',
            'title': title,
            'message': message,
            'notification_type': notification_type
        }
    )

def notify_order_assigned(order, courier_user_id):
    "Уведомление курьера о новом заказе"
    channel_layer = get_channel_layer()
    
    async_to_sync(channel_layer.group_send)(
        f'orders_{courier_user_id}',
        {
            'type': 'new_order',
            'order_id': order.id,
            'pickup_address': order.pickup_address[:50],
            'delivery_address': order.delivery_address[:50],
            'order_type': order.get_order_type_display(),
            'weight': str(order.weight) if order.weight else 'не указан',
            'created_at': order.created_at.strftime('%d.%m.%Y %H:%M')
        }
    )