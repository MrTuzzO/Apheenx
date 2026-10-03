from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone

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
    thumbnail = models.ImageField(upload_to='video_thumbnails/', blank=True, null=True, max_length=500)
    trailer = models.FileField(upload_to='video_trailers/', blank=True, null=True, max_length=500)
    main_video = models.FileField(upload_to='videos/', blank=True, null=True, max_length=500)
    duration = models.PositiveIntegerField(null=True, blank=True, help_text='Video duration in seconds')
    views_count = models.PositiveIntegerField(default=0)
    income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_featured = models.BooleanField(default=False, db_index=True)

    cf_stream_uid = models.CharField(max_length=100, blank=True, null=True, help_text="Cloudflare Stream UID")

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

    def save(self, *args, **kwargs):
        # Check if the main_video was changed
        video_changed = False
        old_cf_uid = None
        old_main_video = None
        old_trailer = None
        old_thumbnail = None

        if self.pk:
            old_obj = Video.objects.filter(pk=self.pk).first()
            if old_obj:
                if old_obj.main_video != self.main_video:
                    old_cf_uid = old_obj.cf_stream_uid
                    old_main_video = old_obj.main_video
                    self.cf_stream_uid = None  # Clear old UID
                    video_changed = True
                
                if old_obj.trailer != self.trailer:
                    old_trailer = old_obj.trailer
                if old_obj.thumbnail != self.thumbnail:
                    old_thumbnail = old_obj.thumbnail
        else:
            if self.main_video:
                video_changed = True

        super().save(*args, **kwargs)
        
        # Cleanup replaced files from Cloudflare and R2
        try:
            from .cloudflare_service import delete_video_from_cloudflare_stream
            if old_cf_uid:
                delete_video_from_cloudflare_stream(old_cf_uid)
            if old_main_video:
                old_main_video.delete(save=False)
            if old_trailer:
                old_trailer.delete(save=False)
            if old_thumbnail:
                old_thumbnail.delete(save=False)
        except Exception:
            pass

        # Only ingest if video changed and we don't have a stream uid yet
        if self.main_video and not self.cf_stream_uid and video_changed:
            try:
                from .cloudflare_service import ingest_video_to_cloudflare_stream
                # R2 থেকে পাবলিক/সাইন্ড লিংক জেনারেট করে Cloudflare Stream-এ পাঠানো হচ্ছে
                video_url = self.main_video.url 
                uid = ingest_video_to_cloudflare_stream(video_url)
                if uid:
                    self.cf_stream_uid = uid
                    # শুধুমাত্র cf_stream_uid আপডেট করছি
                    super().save(update_fields=['cf_stream_uid'])
            except Exception as e:
                pass

    def delete(self, *args, **kwargs):
        from .cloudflare_service import delete_video_from_cloudflare_stream
        # Delete from Cloudflare Stream
        if self.cf_stream_uid:
            try:
                delete_video_from_cloudflare_stream(self.cf_stream_uid)
            except Exception:
                pass
        
        # Delete files from R2
        try:
            if self.main_video:
                self.main_video.delete(save=False)
            if self.trailer:
                self.trailer.delete(save=False)
            if self.thumbnail:
                self.thumbnail.delete(save=False)
        except Exception:
            pass
            
        super().delete(*args, **kwargs)



class VideoOrder(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='video_orders',)
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='orders')
    paypal_order_id = models.CharField(max_length=150, unique=True, null=True, blank=True)
    paypal_approval_url = models.URLField(max_length=500, null=True, blank=True)
    paypal_order_expires_at = models.DateTimeField(null=True, blank=True, db_index=True)

    stripe_payment_intent_id = models.CharField(max_length=255, unique=True, null=True, blank=True)

    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='pending', db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'video')
        indexes = [
            models.Index(fields=['payment_status', 'created_at'], name='videoord_pay_created_idx'),
            models.Index(fields=['payment_status', 'video'], name='videoord_pay_video_idx'),
        ]

    @property
    def is_paid(self):
        return self.payment_status == 'captured'

    # @property
    # def is_paypal_order_active(self):
    #     return bool(
    #         self.paypal_order_id
    #         and self.paypal_approval_url
    #         and self.paypal_order_expires_at
    #         and timezone.now() < self.paypal_order_expires_at
    #     )

    def __str__(self):
        return f'{self.user} | {self.video.title} | {self.payment_status}'
