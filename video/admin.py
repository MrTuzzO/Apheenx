from django.contrib import admin

from .models import Video, VideoCategory, VideoOrder


@admin.register(VideoCategory)
class VideoCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'category', 'price', 'status',
        'income', 'views_count', 'created_at',
    )
    list_filter = ('status', 'is_featured', 'category')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('views_count', 'created_at', 'updated_at', 'income')
    list_per_page = 25
    ordering = ('-created_at',)

    @admin.display(description='Duration')
    def duration_display(self, obj):
        return obj.duration_display or '—'


@admin.register(VideoOrder)
class VideoOrderAdmin(admin.ModelAdmin):
    list_display = ('user', 'video', 'paypal_order_id', 'created_at', 'payment_status', 'amount')
    list_filter = ('payment_status',)
    search_fields = ('user__email', 'video__title', 'paypal_order_id')
    raw_id_fields = ('user', 'video')
    readonly_fields = ('created_at',)
