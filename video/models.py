from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

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
    trailer = models.FileField(upload_to='video_trailers/', blank=True, null=True)
    main_video = models.FileField(upload_to='videos/', blank=True, null=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} - {self.category.name} - {self.price} - {self.status}'