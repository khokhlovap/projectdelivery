from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.contrib.auth.base_user import BaseUserManager

class CustomUserManager(BaseUserManager):
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
    username = None  # убираем username
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    patronymic = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = CustomUserManager()

class Role(models.Model):
    ROLE_CHOICES = (
        ('client', 'Клиент'),
        ('courier', 'Курьер'),
        ('manager', 'Менеджер'),
    )
    name = models.CharField(max_length=20, choices=ROLE_CHOICES, unique=True)

    def __str__(self):
        return self.get_name_display()

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    company = models.CharField(max_length=255, blank=True, null=True)
    department = models.CharField(max_length=255, blank=True, null=True)
    role = models.ForeignKey(Role, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.user.email} ({self.role})"
    
class Courier(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    education = models.CharField(max_length=255, blank=True, null=True)
    position = models.CharField(max_length=255, default="Курьер")

    def is_available(self):
        today = timezone.now().date()
        return not Vacation.objects.filter(
            courier=self,
            start_date__lte=today,
            end_date__gte=today
        ).exists()

    def __str__(self):
        return f"{self.user.last_name} {self.user.first_name}"
    
class Vacation(models.Model):
    courier = models.ForeignKey(Courier, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return f"Отпуск {self.courier} ({self.start_date} – {self.end_date})"


class Manager(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    education = models.CharField(max_length=255, blank=True, null=True)
    position = models.CharField(max_length=255, default="Менеджер")

    def __str__(self):
        return f"{self.user.last_name} {self.user.first_name}"

class OrderType(models.Model):
    name = models.CharField(
        max_length=50,
        choices=(
            ('documents', 'Документация'),
            ('gifts', 'Подарки'),
        )
    )

    def __str__(self):
        return self.get_name_display()

class Order(models.Model):
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    courier = models.ForeignKey(Courier, on_delete=models.SET_NULL, null=True, blank=True)
    order_type = models.ForeignKey(OrderType, on_delete=models.PROTECT)
    city = models.CharField(max_length=100)
    street = models.CharField(max_length=255)
    house = models.CharField(max_length=20)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Заказ #{self.id}"
    
class OrderStatus(models.Model):
    STATUS_CHOICES = (
        ('created', 'Создан'),
        ('assigned', 'Назначен курьер'),
        ('in_progress', 'В работе'),
        ('delivered', 'Доставлен'),
        ('cancelled', 'Отменён'),
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='statuses')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.order} – {self.get_status_display()}"

class Payment(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE)

    STATUS_CHOICES = (
        ('pending', 'Ожидает оплаты'),
        ('paid', 'Оплачено'),
        ('failed', 'Ошибка оплаты'),
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    receipt = models.FileField(upload_to='receipts/', blank=True, null=True)

    def __str__(self):
        return f"Оплата заказа #{self.order.id}"

class CourierRating(models.Model):
    client = models.ForeignKey(User, on_delete=models.CASCADE)
    courier = models.ForeignKey(Courier, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.rating} — {self.courier}"
    
class TelegramProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telegram_id = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"TG {self.user.email}"

class AIChatLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.TextField()
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


