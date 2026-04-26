from rest_framework import serializers
from .models import Order, OrderItem, PAYMENT_STATUS_CHOICES, ORDER_STATUS_CHOICES
from video.models import VideoOrder

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'unit_price', 'subtotal']
        read_only_fields = fields

    def get_subtotal(self, obj):
        return obj.subtotal


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    is_paid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'full_name', 'email', 'phone', 'address', 'city', 'state', 'postal_code', 'country',
            'paypal_order_id', 'payment_status', 'is_paid', 'order_status', 'total_price',
            'items', 'created_at', 'updated_at',
        ]
        read_only_fields = fields


class CartItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class CreateOrderSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    address = serializers.CharField(max_length=255)
    city = serializers.CharField(max_length=100)
    state = serializers.CharField(max_length=2, min_length=2)
    postal_code = serializers.CharField(max_length=20)
    country = serializers.CharField(max_length=100)
    items = CartItemSerializer(many=True)

    def validate_state(self, value):
        return value.upper()

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Cart is empty.")
        ids = [i['product_id'] for i in value]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Duplicate product_id in items.")
        return value


class UpdateOrderStatusSerializer(serializers.Serializer):
    order_status = serializers.ChoiceField(choices=ORDER_STATUS_CHOICES)


# ______Video Order Serializer______

class VideoOrderSerializer(serializers.ModelSerializer):
    video_title = serializers.CharField(source='video.title', read_only=True)
    video_thumbnail = serializers.SerializerMethodField()
    is_paid = serializers.BooleanField(read_only=True)
    video_slug = serializers.CharField(source='video.slug', read_only=True)

    class Meta:
        model = VideoOrder
        fields = [
            'id', 'video', 'video_title', 'video_slug', 'video_thumbnail',
            'paypal_order_id', 'payment_status', 'is_paid',
            'amount', 'created_at',
        ]
        read_only_fields = fields

    def get_video_thumbnail(self, obj):
        if not obj.video.thumbnail:
            return None
        url = obj.video.thumbnail.url
        request = self.context.get('request')
        return request.build_absolute_uri(url) if request else url


class CreateVideoOrderSerializer(serializers.Serializer):
    video_id = serializers.IntegerField()
