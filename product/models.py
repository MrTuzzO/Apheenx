from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

STATUS_CHOICES = (
    ('draft', 'Draft'),
    ('active', 'Active'),
)

class ProductCategory(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = 'Product Categories'
    

class Product(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    stock = models.PositiveIntegerField()
    price_off = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(0), MaxValueValidator(100)], help_text='Discount percentage (0-100)')
    category = models.ForeignKey(ProductCategory, related_name='products', on_delete=models.CASCADE, db_index=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft', db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def final_price(self):
        if self.price_off:
            return self.price - (self.price * self.price_off / 100)
        return self.price

    def __str__(self):
        return f'{self.name} - {self.category.name} - {self.price} - {self.stock} - {self.status}'
    

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/')

    def __str__(self):
        return f'Image for {self.product.name}'