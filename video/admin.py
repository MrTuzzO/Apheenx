from django.contrib import admin
from .models import Video, VideoCategory

@admin.register(VideoCategory)
class VideoCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'price', 'status', 'is_featured', 'created_at', 'updated_at')
    list_filter = ('status', 'is_featured', 'category')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}