from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator

PAYMENT_STATUS_CHOICES = (
    ('pending', 'Pending'),
    ('captured', 'Captured'),
    ('failed', 'Failed'),
    ('refunded', 'Refunded'),
)

STATUS_CHOICES = (
    ('draft', 'Draft'),
    ('published', 'Published'),
)

class VideoCategory(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Video Categories'


class Video(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    category = models.ForeignKey(VideoCategory, related_name='videos', on_delete=models.CASCADE, db_index=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft', db_index=True)
    thumbnail = models.ImageField(upload_to='video_thumbnails/', blank=True, null=True)
    trailer = models.FileField(upload_to='video_trailers/')
    main_video = models.FileField(upload_to='videos/', blank=True, null=True)
    duration = models.PositiveIntegerField(null=True, blank=True, help_text='Video duration in seconds')
    views_count = models.PositiveIntegerField(default=0)
    income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_featured = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} - {self.category.name} - {self.price} - {self.status}'

    @property
    def duration_display(self):
        if not self.duration:
            return None
        hours, remainder = divmod(self.duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f'{hours:02d}:{minutes:02d}:{seconds:02d}'
        return f'{minutes:02d}:{seconds:02d}'


class VideoOrder(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='video_orders',)
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='orders')
    paypal_order_id = models.CharField(max_length=150, unique=True, null=True, blank=True)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='pending', db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'video')

    @property
    def is_paid(self):
        return self.payment_status == 'captured'

    def __str__(self):
        return f'{self.user} | {self.video.title} | {self.payment_status}'