from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.contrib.auth.base_user import BaseUserManager


class CustomUserManager(BaseUserManager):
    "Кастомный менеджер пользователей с email в качестве идентификатора"
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email должен быть указан')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser должен иметь is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser должен иметь is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True, verbose_name='Email профиля')
    first_name = models.CharField(max_length=100, verbose_name='Имя')
    last_name = models.CharField(max_length=100, verbose_name='Фамилия')
    patronymic = models.CharField(max_length=100, blank=True, null=True, verbose_name='Отчество')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='Телефон')
    birth_date = models.DateField(blank=True, null=True, verbose_name='Дата рождения')
    
    ROLE_CHOICES = (
        ('client', 'Клиент'),
        ('manager', 'Менеджер'),
        ('courier', 'Курьер'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='client', verbose_name='Роль')
    
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = CustomUserManager()

    def __str__(self):
        return f"{self.last_name} {self.first_name} ({self.email})"

    def get_full_name(self):
        if self.patronymic:
            return f"{self.last_name} {self.first_name} {self.patronymic}"
        return f"{self.last_name} {self.first_name}"

    class Meta:
        db_table = 'users'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'


class Client(models.Model):
    "Модель клиента (юридического лица)"
    user = models.OneToOneField(User, on_delete=models.CASCADE, 
                                primary_key=True, related_name='client_profile')
    
    company_name = models.CharField(max_length=255, verbose_name='Название компании')
    inn = models.CharField(max_length=12, verbose_name='ИНН')
    kpp = models.CharField(max_length=9, verbose_name='КПП')
    ogrn = models.CharField(max_length=15, blank=True, verbose_name='ОГРН')
    okpo = models.CharField(max_length=10, blank=True, verbose_name='ОКПО')
    
    country = models.CharField(max_length=100, default='Россия', verbose_name='Страна')
    city = models.CharField(max_length=100, default='Москва', verbose_name='Город')
    legal_address = models.TextField(verbose_name='Юридический адрес')
    actual_address = models.TextField(verbose_name='Фактический адрес')
    
    company_phone = models.CharField(max_length=20, verbose_name='Телефон компании')
    company_email = models.EmailField(verbose_name='E-mail компании')
    
    bank = models.CharField(max_length=255, verbose_name='Банк')
    settlement_account = models.CharField(max_length=20, verbose_name='Расчетный счет')
    correspondent_account = models.CharField(max_length=20, verbose_name='Корреспондентский счет')
    
    contact_person_first_name = models.CharField(max_length=100, verbose_name='Имя контактного лица')
    contact_person_last_name = models.CharField(max_length=100, verbose_name='Фамилия контактного лица')
    contact_person_patronymic = models.CharField(max_length=100, blank=True, verbose_name='Отчество контактного лица')
    contact_person_phone = models.CharField(max_length=20, verbose_name='Телефон контактного лица')
    contact_person_email = models.EmailField(verbose_name='E-mail контактного лица')
    
    def __str__(self):
        return self.company_name

    def get_contact_person_full_name(self):
        if self.contact_person_patronymic:
            return f"{self.contact_person_last_name} {self.contact_person_first_name} {self.contact_person_patronymic}"
        return f"{self.contact_person_last_name} {self.contact_person_first_name}"

    class Meta:
        db_table = 'clients'
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'


class ClientAdditionalInfo(models.Model):
    "Дополнительные сведения о клиенте (комментарии менеджера)"

    client = models.OneToOneField(Client, on_delete=models.CASCADE, 
                                  related_name='additional_info')
    comment = models.TextField(blank=True, verbose_name='Комментарий от менеджера')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Доп. информация: {self.client.company_name}"

    class Meta:
        db_table = 'clients_additional_info'
        verbose_name = 'Доп. информация о клиенте'
        verbose_name_plural = 'Доп. информация о клиентах'


class Manager(models.Model):
    "Модель менеджера"
    user = models.OneToOneField(User, on_delete=models.CASCADE, 
                                primary_key=True, related_name='manager_profile')
    position = models.CharField(max_length=255, default='Менеджер', verbose_name='Должность')

    def __str__(self):
        return self.user.get_full_name()

    class Meta:
        db_table = 'managers'
        verbose_name = 'Менеджер'
        verbose_name_plural = 'Менеджеры'


class Courier(models.Model):
    "Модель курьера"
    user = models.OneToOneField(User, on_delete=models.CASCADE, 
                                primary_key=True, related_name='courier_profile')
    
    hire_date = models.DateField(verbose_name='Дата приема на работу')
    position = models.CharField(max_length=255, default='Курьер', verbose_name='Должность')
    
    SHIFT_STATUS_CHOICES = (
        ('off', 'Не на смене'),
        ('on', 'На смене'),
        ('break', 'На перерыве'),
    )
    shift_status = models.CharField(
        max_length=10, 
        choices=SHIFT_STATUS_CHOICES, 
        default='off',
        verbose_name='Статус смены'
    )
    
    total_orders = models.IntegerField(default=0, verbose_name='Всего заказов')
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0, verbose_name='Средний рейтинг')
    total_work_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name='Всего отработано часов')
    total_shifts = models.IntegerField(default=0, verbose_name='Всего смен')
    
    citizenship = models.CharField(max_length=100, verbose_name='Гражданство')
    passport_series = models.CharField(max_length=4, verbose_name='Серия паспорта')
    passport_number = models.CharField(max_length=6, verbose_name='Номер паспорта')
    passport_department_code = models.CharField(max_length=7, verbose_name='Код подразделения')
    passport_issued_by = models.CharField(max_length=255, verbose_name='Кем выдан')
    passport_issue_date = models.DateField(verbose_name='Дата выдачи')
    
    registration_address = models.TextField(verbose_name='Адрес регистрации')
    actual_address = models.TextField(verbose_name='Фактический адрес проживания')
    
    def is_available(self):
        "Проверка доступности курьера для назначения заказа"
        if self.shift_status != 'on':
            return False
        
        today = timezone.now().date()
        
        has_vacation = Vacation.objects.filter(
            courier=self,
            start_date__lte=today,
            end_date__gte=today
        ).exists()
        
        has_sick_leave = SickLeave.objects.filter(
            courier=self,
            start_date__lte=today,
            end_date__gte=today
        ).exists()
        
        return not (has_vacation or has_sick_leave)

    def update_rating(self):
        "Обновление среднего рейтинга курьера"
        from django.db.models import Avg
        avg = OrderRating.objects.filter(courier=self).aggregate(Avg('rating'))['rating__avg']
        self.avg_rating = avg if avg else 0
        self.save(update_fields=['avg_rating'])

    def __str__(self):
        return self.user.get_full_name()

    class Meta:
        db_table = 'couriers'
        verbose_name = 'Курьер'
        verbose_name_plural = 'Курьеры'


class CourierAdditionalInfo(models.Model):
    "Дополнительные сведения о курьере (комментарии менеджера)"

    courier = models.OneToOneField(Courier, on_delete=models.CASCADE, 
                                   related_name='additional_info')
    comment = models.TextField(blank=True, verbose_name='Комментарий от менеджера')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Доп. информация: {self.courier.user.get_full_name()}"

    class Meta:
        db_table = 'couriers_additional_info'
        verbose_name = 'Доп. информация о курьере'
        verbose_name_plural = 'Доп. информация о курьерах'


class Vacation(models.Model):
    "Отпуск курьера"

    courier = models.ForeignKey(Courier, on_delete=models.CASCADE, 
                                related_name='vacations')
    start_date = models.DateField(verbose_name='Дата начала отпуска')
    end_date = models.DateField(verbose_name='Дата окончания отпуска')

    def clean(self):
        "Валидация перед сохранением"
        if self.end_date < self.start_date:
            raise ValidationError({'end_date': 'Дата окончания не может быть раньше даты начала'})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Отпуск {self.courier.user.get_full_name()} ({self.start_date} – {self.end_date})"

    class Meta:
        db_table = 'vacations'
        verbose_name = 'Отпуск'
        verbose_name_plural = 'Отпуска'


class SickLeave(models.Model):
    "Больничный лист курьера"

    courier = models.ForeignKey(Courier, on_delete=models.CASCADE, 
                                related_name='sick_leaves')
    start_date = models.DateField(verbose_name='Дата начала болезни')
    end_date = models.DateField(verbose_name='Дата окончания болезни')
    comment = models.TextField(blank=True, verbose_name='Комментарий')
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        "Валидация перед сохранением"
        if self.end_date < self.start_date:
            raise ValidationError({'end_date': 'Дата окончания не может быть раньше даты начала'})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Больничный {self.courier.user.get_full_name()} ({self.start_date} – {self.end_date})"

    class Meta:
        db_table = 'sick_leaves'
        verbose_name = 'Больничный лист'
        verbose_name_plural = 'Больничные листы'


class CourierShift(models.Model):
    "Рабочая смена курьера (история)"
    courier = models.ForeignKey(Courier, on_delete=models.CASCADE, 
                                related_name='shifts')
    
    start_time = models.DateTimeField(verbose_name='Начало смены')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='Конец смены')
    
    total_break_minutes = models.IntegerField(default=0, verbose_name='Общее время перерывов (минуты)')
    orders_completed = models.IntegerField(default=0, verbose_name='Заказов выполнено за смену')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def clean(self):
        "Валидация перед сохранением"
        if self.end_time and self.end_time < self.start_time:
            raise ValidationError({'end_time': 'Время окончания не может быть раньше времени начала'})
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def get_duration(self):
        "Продолжительность смены в часах (без учёта перерывов)"
        if not self.end_time:
            return None
        
        if self.end_time < self.start_time:
            return 0
        
        duration = self.end_time - self.start_time
        duration_minutes = duration.total_seconds() / 60 - self.total_break_minutes
        
        if duration_minutes < 0:
            return 0
        
        return round(duration_minutes / 60, 2)
    
    def end_shift(self):
        "Завершить смену с атомарным обновлением статистики"
        if self.end_time:
            raise ValidationError('Смена уже завершена')
        
        self.end_time = timezone.now()
        
        if self.end_time < self.start_time:
            self.end_time = timezone.now()
        
        self.save()
        
        duration = self.get_duration()
        if duration and duration > 0:
            Courier.objects.filter(pk=self.courier.pk).update(
                total_work_hours=F('total_work_hours') + duration,
                total_shifts=F('total_shifts') + 1,
                shift_status='off'
            )
    
    def __str__(self):
        return f"Смена {self.courier.user.get_full_name()} - {self.start_time.strftime('%d.%m.%Y %H:%M')}"

    class Meta:
        db_table = 'courier_shifts'
        ordering = ['-start_time']
        verbose_name = 'Смена курьера'
        verbose_name_plural = 'Смены курьеров'


class CourierShiftBreak(models.Model):
    "Перерыв внутри смены"

    shift = models.ForeignKey(CourierShift, on_delete=models.CASCADE, 
                              related_name='breaks')
    
    start_time = models.DateTimeField(verbose_name='Начало перерыва')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='Конец перерыва')
    
    def clean(self):
        """Валидация перед сохранением"""
        if self.end_time and self.end_time < self.start_time:
            raise ValidationError({'end_time': 'Время окончания не может быть раньше времени начала'})
        
        if self.start_time < self.shift.start_time:
            raise ValidationError({'start_time': 'Перерыв не может начаться раньше начала смены'})
        
        if self.end_time and self.shift.end_time and self.end_time > self.shift.end_time:
            raise ValidationError({'end_time': 'Перерыв не может закончиться позже окончания смены'})
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def get_duration_minutes(self):
        "Продолжительность перерыва в минутах"
        if not self.end_time:
            return None
        
        if self.end_time < self.start_time:
            return 0
        
        duration = self.end_time - self.start_time
        return int(duration.total_seconds() / 60)
    
    def end_break(self):
        "Завершить перерыв с атомарным обновлением статистики смены"
        if self.end_time:
            raise ValidationError('Перерыв уже завершён')
        
        self.end_time = timezone.now()
        
        if self.end_time < self.start_time:
            self.end_time = timezone.now()
        
        self.save()
        
        duration = self.get_duration_minutes()
        if duration and duration > 0:
            CourierShift.objects.filter(pk=self.shift.pk).update(
                total_break_minutes=F('total_break_minutes') + duration
            )
    
    def __str__(self):
        return f"Перерыв в смене {self.shift.id}"

    class Meta:
        db_table = 'courier_shifts_breaks'
        verbose_name = 'Перерыв в смене'
        verbose_name_plural = 'Перерывы в сменах'


class Order(models.Model):
    "Модель заказа"
    client = models.ForeignKey(Client, on_delete=models.PROTECT, 
                               related_name='orders', verbose_name='Клиент')
    courier = models.ForeignKey(Courier, on_delete=models.SET_NULL, 
                                null=True, blank=True, related_name='orders',
                                verbose_name='Курьер')
    manager = models.ForeignKey(Manager, on_delete=models.SET_NULL, 
                                null=True, blank=True, related_name='managed_orders',
                                verbose_name='Менеджер')
    
    ORDER_TYPE_CHOICES = (
        ('documents', 'Документация'),
        ('gifts', 'Подарки'),
    )
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES, verbose_name='Тип заказа')
    
    TARIFF_CHOICES = (
        ('standard', 'Стандартный'),
        ('24_hours', '24 часа'),
        ('working', 'Рабочий'),
        ('fast', 'Быстрый'),
        ('per_hour', 'За час'),
    )
    tariff = models.CharField(max_length=20, choices=TARIFF_CHOICES, default='standard', verbose_name='Тариф доставки')
    
    weight = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, verbose_name='Вес (кг)')
    client_comment = models.TextField(blank=True, verbose_name='Комментарий от клиента')
    
    pickup_address = models.TextField(verbose_name='Адрес отправки')
    delivery_address = models.TextField(verbose_name='Адрес доставки')
    
    recipient_first_name = models.CharField(max_length=100, verbose_name='Имя получателя')
    recipient_last_name = models.CharField(max_length=100, verbose_name='Фамилия получателя')
    recipient_patronymic = models.CharField(max_length=100, blank=True, verbose_name='Отчество получателя')
    recipient_phone = models.CharField(max_length=20, verbose_name='Телефон получателя')
    recipient_company = models.CharField(max_length=255, blank=True, verbose_name='Компания получателя')
    
    requested_delivery_date = models.DateField(verbose_name='Желаемая дата доставки')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    delivered_at = models.DateTimeField(blank=True, null=True, verbose_name='Дата и время доставки')
    
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Сумма')
    invoice_number = models.CharField(max_length=50, blank=True, verbose_name='Номер счета')
    
    STATUS_CHOICES = (
        ('created', 'Создан'),
        ('pending', 'Ожидает назначения'),
        ('assigned', 'Назначен курьер'),
        ('in_progress', 'В пути'),
        ('delivered', 'Доставлен'),
        ('cancelled', 'Отменён'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created', verbose_name='Статус заказа')
    
    PAYMENT_CHOICES = (
        ('created', 'Счет создан'),
        ('sent', 'Счет отправлен'),
        ('paid', 'Оплачено'),
        ('failed', 'Ошибка оплаты'),
    )
    payment_status = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='created', 
                                      verbose_name='Статус оплаты')
    
    def clean(self):
        "Валидация перед сохранением"
        if self.pk is None and self.requested_delivery_date < timezone.now().date():
            raise ValidationError({'requested_delivery_date': 'Желаемая дата доставки не может быть в прошлом'})
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Заказ №{self.id} от {self.created_at.strftime('%d.%m.%Y')}"

    def get_recipient_full_name(self):
        if self.recipient_patronymic:
            return f"{self.recipient_last_name} {self.recipient_first_name} {self.recipient_patronymic}"
        return f"{self.recipient_last_name} {self.recipient_first_name}"

    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['client', 'status']),
            models.Index(fields=['courier', 'status']),
        ]
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'


class OrderStatusHistory(models.Model):
    "История изменения статусов заказа"
    order = models.ForeignKey(Order, on_delete=models.CASCADE, 
                              related_name='status_history', verbose_name='Заказ')
    status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES, verbose_name='Статус')
    changed_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата и время изменения')
    comment = models.TextField(blank=True, verbose_name='Комментарий')

    def __str__(self):
        return f"{self.order} – {self.get_status_display()} в {self.changed_at}"

    class Meta:
        db_table = 'order_status_history'
        ordering = ['changed_at']
        verbose_name = 'История статуса'
        verbose_name_plural = 'История статусов'


class OrderRating(models.Model):
    "Оценка заказа (клиентом курьера). Только оценка, без комментария"
    order = models.OneToOneField(Order, on_delete=models.CASCADE, 
                                 related_name='rating', verbose_name='Заказ')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, 
                               related_name='ratings', verbose_name='Клиент')
    courier = models.ForeignKey(Courier, on_delete=models.CASCADE, 
                                related_name='ratings', verbose_name='Курьер')
    rating = models.PositiveSmallIntegerField(verbose_name='Оценка (1-5)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата оценки')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        self.courier.update_rating()
        
        if self.order.status == 'delivered':
            Courier.objects.filter(pk=self.courier.pk).update(
                total_orders=F('total_orders') + 1
            )
            
            current_shift = CourierShift.objects.filter(
                courier=self.courier,
                end_time__isnull=True
            ).first()
            
            if current_shift:
                CourierShift.objects.filter(pk=current_shift.pk).update(
                    orders_completed=F('orders_completed') + 1
                )

    def __str__(self):
        return f"Оценка {self.rating} для {self.courier.user.get_full_name()} (заказ №{self.order.id})"

    class Meta:
        db_table = 'order_ratings'
        verbose_name = 'Оценка заказа'
        verbose_name_plural = 'Оценки заказов'


class Payment(models.Model):
    "Оплата заказа"
    order = models.OneToOneField(Order, on_delete=models.CASCADE, 
                                 related_name='payment', verbose_name='Заказ')
    
    STATUS_CHOICES = (
        ('created', 'Счет создан'),
        ('sent', 'Счет отправлен'),
        ('paid', 'Оплачено'),
        ('failed', 'Ошибка оплаты'),
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created', verbose_name='Статус оплаты')
    comment = models.TextField(blank=True, null=True, verbose_name='Комментарий')
    receipt = models.FileField(upload_to='receipts/', blank=True, null=True, verbose_name='Чек')
    paid_at = models.DateTimeField(blank=True, null=True, verbose_name='Дата оплаты')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания счета')

    def __str__(self):
        return f"Оплата заказа №{self.order.id} – {self.get_status_display()}"

    class Meta:
        db_table = 'payments'
        verbose_name = 'Оплата'
        verbose_name_plural = 'Оплаты'


class AIChatKnowledgeBase(models.Model):
    "База знаний для AI-чата (заготовленные вопросы и ответы)"
    question = models.TextField(verbose_name='Вопрос')
    answer = models.TextField(verbose_name='Ответ')
    keywords = models.CharField(max_length=255, blank=True, verbose_name='Ключевые слова')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.question[:50]

    class Meta:
        db_table = 'ai_chat_knowledge_base'
        verbose_name = 'База знаний AI-чата'
        verbose_name_plural = 'База знаний AI-чата'


class AIChatLog(models.Model):
    """
    История вопросов пользователей к AI-чату.
    Используется для анализа популярных запросов.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, 
                             related_name='ai_chat_logs', verbose_name='Пользователь')
    question = models.TextField(verbose_name='Вопрос пользователя')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата и время запроса')

    def __str__(self):
        return f"{self.user.email} – {self.created_at.strftime('%d.%m.%Y %H:%M')}"

    class Meta:
        db_table = 'ai_chat_logs'
        ordering = ['-created_at']
        verbose_name = 'Лог AI-чата'
        verbose_name_plural = 'Логи AI-чата'

class CourierNotification(models.Model):
    """Уведомления для курьера о новых заказах"""
    courier = models.ForeignKey(Courier, on_delete=models.CASCADE, related_name='notifications')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField(verbose_name='Сообщение')
    is_read = models.BooleanField(default=False, verbose_name='Прочитано')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    
    NOTIFICATION_TYPES = (
        ('new', 'Новый заказ'),
        ('reminder', 'Напоминание'),
        ('rejected', 'Отклонен'),
    )
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='new')
    
    def __str__(self):
        return f"Уведомление для {self.courier.user.get_full_name()} - {self.order.id}"
    
    class Meta:
        db_table = 'courier_notifications'
        ordering = ['-created_at']
        verbose_name = 'Уведомление курьера'
        verbose_name_plural = 'Уведомления курьеров'