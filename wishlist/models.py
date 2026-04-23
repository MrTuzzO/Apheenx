from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class WishlistItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist_items")
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, limit_choices_to={"model__in": ("product", "video")})
    object_id = models.PositiveIntegerField()
    item = GenericForeignKey("content_type", "object_id")
    added_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ("user", "content_type", "object_id")
        ordering = ["-added_at"]
        indexes = [models.Index(fields=["user", "content_type", "object_id"])]

    def __str__(self):
        return f"{self.user_id} → {self.content_type.model}:{self.object_id}"