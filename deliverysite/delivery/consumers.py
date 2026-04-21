import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

class OrderConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.room_group_name = f'orders_{self.user_id}'
        
        # Проверка аутентификации
        if self.scope['user'].is_authenticated:
            # Присоединяемся к комнате
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
            print(f"WebSocket подключен: user {self.user_id}")
            
            # Отправляем приветственное сообщение
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': 'WebSocket connected',
                'user_id': self.user_id
            }))
        else:
            await self.close()

    async def disconnect(self, close_code):
        # Отключаемся от комнаты
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        print(f"WebSocket отключен: user {self.user_id}")

    # Получение сообщений от клиента
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'ping':
            await self.send(text_data=json.dumps({
                'type': 'pong',
                'timestamp': str(timezone.now())
            }))

    # Отправка обновления статуса
    async def order_status_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'order_status_update',
            'order_id': event['order_id'],
            'status': event['status'],
            'status_display': event['status_display'],
            'updated_at': event['updated_at'],
            'courier_name': event.get('courier_name', '')
        }))

    # Отправка нового заказа для курьера
    async def new_order(self, event):
        await self.send(text_data=json.dumps({
            'type': 'new_order',
            'order_id': event['order_id'],
            'pickup_address': event['pickup_address'],
            'delivery_address': event['delivery_address'],
            'order_type': event['order_type'],
            'weight': event['weight'],
            'created_at': event['created_at']
        }))

    # Отправка уведомления
    async def notification(self, event):
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'title': event['title'],
            'message': event['message'],
            'notification_type': event['notification_type']
        }))