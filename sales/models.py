from django.db import models
from django.core.validators import MinValueValidator
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.utils import timezone


class Customer(models.Model):
    full_name = models.CharField(max_length=255, verbose_name='ФИО')
    email = models.EmailField(unique=True, verbose_name='Email')
    company_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Компания'
    )
    phone = models.CharField(max_length=20, verbose_name='Телефон')
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата регистрации'
    )
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='Персональная скидка (%)',
        validators=[MinValueValidator(0)]
    )

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    class Meta:
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'
        ordering = ['-created_at']


class Product(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Цена (KGS)'
    )
    stock_quantity = models.PositiveIntegerField(
        verbose_name='Остаток на складе'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Доступен для заказа'
    )
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='Скидка на товар (%)',
        validators=[MinValueValidator(0)]
    )

    def __str__(self):
        return f"{self.name} - {self.price} KGS"

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['name']


class Order(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('confirmed', 'Подтвержден'),
        ('shipped', 'Отправлен'),
        ('cancelled', 'Отменен'),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name='Клиент'
    )
    products = models.ManyToManyField(
        Product,
        through='OrderItem',
        verbose_name='Товары'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='Статус'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    delivery_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=500,
        verbose_name='Стоимость доставки',
        validators=[MinValueValidator(0)]
    )
    tax_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=12,
        verbose_name='НДС (%)',
        validators=[MinValueValidator(0)]
    )

    @property
    def subtotal(self):
        """Сумма по позициям без учета скидок и налогов"""
        return sum(
            item.price * item.quantity
            for item in self.items.all()
        )

    @property
    def total_discounts(self):
        """Общая сумма всех скидок"""
        # Скидки на товары
        product_discounts = sum(
            item.product.discount_percent / 100 * item.price * item.quantity
            for item in self.items.all()
        )

        # Скидка клиента
        customer_discount = self.customer.discount_percent / 100 * self.subtotal

        # Глобальная скидка 10% при заказе > 150000 KGS
        global_discount = 0
        if self.subtotal > 150000:
            global_discount = self.subtotal * 0.1

        return product_discounts + customer_discount + global_discount

    @property
    def total_tax(self):
        """Сумма налогов"""
        return self.subtotal * (self.tax_percent / 100)

    @property
    def total_delivery(self):
        """Стоимость доставки (бесплатно при заказе > 2000 KGS)"""
        return 0 if self.subtotal > 2000 else self.delivery_cost

    @property
    def total_amount(self):
        """Итоговая сумма к оплате"""
        return (
                self.subtotal
                - self.total_discounts
                + self.total_tax
                + self.total_delivery
        )

    def save(self, *args, **kwargs):
        """Списание товаров при подтверждении заказа"""
        if self.status == 'confirmed':
            if self.pk:  # Если заказ уже существует
                original = Order.objects.get(pk=self.pk)
                if original.status != 'confirmed':  # Если статус изменился
                    for item in self.items.all():
                        product = item.product
                        product.stock_quantity -= item.quantity
                        product.save()
            else:  # Если заказ новый
                for item in self.items.all():
                    product = item.product
                    product.stock_quantity -= item.quantity
                    product.save()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Заказ #{self.id} - {self.customer.full_name}"

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        verbose_name='Товар'
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name='Количество',
        validators=[MinValueValidator(1)]
    )
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Цена на момент заказа'
    )

    def save(self, *args, **kwargs):
        """Автоматически устанавливаем цену товара при создании"""
        if not self.price:
            self.price = self.product.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} x{self.quantity} ({self.price} KGS)"

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'
        unique_together = ('order', 'product')  # Уникальная пара заказ-товар
