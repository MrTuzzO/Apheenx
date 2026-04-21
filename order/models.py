from django.db import models
from django.conf import settings
from decimal import Decimal
from product.models import Product
from django.core.validators import MinValueValidator


class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='cart', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_price(self):
        return sum(
            (item.subtotal for item in self.items.select_related('product').all()),
            Decimal('0.00'),
        )

    @property
    def total_items(self):
        return sum((item.quantity for item in self.items.all()), 0)

    def __str__(self):
        return f'Cart - {self.user.email}'


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='cart_items', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        unique_together = ('cart', 'product')

    @property
    def subtotal(self):
        return self.product.final_price * self.quantity

    def __str__(self):
        return f'{self.product.name} x {self.quantity}'


ORDER_STATUS_CHOICES = (
    ('pending', 'Pending'),
    ('processing', 'Processing'),
    ('shipped', 'Shipped'),
    ('delivered', 'Delivered'),
    ('cancelled', 'Cancelled'),
)


class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='orders', on_delete=models.CASCADE)
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending', db_index=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Order #{self.id} - {self.user.email} - {self.status}'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='order_items', null=True, on_delete=models.SET_NULL)
    product_name = models.CharField(max_length=255)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f'Order #{self.order.id} - {self.product_name} x {self.quantity}'
