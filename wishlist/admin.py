from django.contrib import admin
from .models import WishlistItem

@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display  = ("user", "content_type", "object_id", "added_at")
    list_filter   = ("content_type",)
    # raw_id_fields = ("user",)
    readonly_fields = ("added_at",)
    search_fields = ("user__email",)