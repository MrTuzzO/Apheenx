from rest_framework import serializers
from product.models import Product
from video.models import Video


class ProductWishlistSerializer(serializers.ModelSerializer):
    # category_name = serializers.CharField(source="category.name", read_only=True)
    final_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id", "name", "slug", "price", "price_off", 
            "final_price", "is_featured","stock", "primary_image",
        )

    def get_primary_image(self, obj):
        images = obj.images.all()
        if not images:
            return None
        request = self.context.get("request")
        url = images[0].image.url
        return request.build_absolute_uri(url) if request else url


class VideoWishlistSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    duration_display = serializers.CharField(read_only=True)

    class Meta:
        model = Video
        fields = (
            "id", "title", "slug", "price", "thumbnail",
            "duration_display", "views_count", "category_name", "is_featured",
        )