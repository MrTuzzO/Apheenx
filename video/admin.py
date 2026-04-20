from django.contrib import admin

from .models import Video, VideoCategory, VideoUnlock


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


@admin.register(VideoUnlock)
class VideoUnlockAdmin(admin.ModelAdmin):
    list_display = ('user', 'video', 'payment_reference', 'unlocked_at')
    list_filter = ('unlocked_at',)
    search_fields = ('user__email', 'video__title', 'payment_reference')
    raw_id_fields = ('user', 'video')
    readonly_fields = ('unlocked_at',)
