from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.db import transaction
from decimal import Decimal

from order.models import Cart, CartItem, Order, OrderItem
from product.models import Product


class CartItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source='product.id', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_slug = serializers.CharField(source='product.slug', read_only=True)
    unit_price = serializers.DecimalField(source='product.final_price', max_digits=10, decimal_places=2, read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'product_id', 'product_name', 'product_slug', 'quantity', 'unit_price', 'subtotal']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_items = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_items', 'total_price', 'updated_at']


class AddCartItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)

    def validate_product_id(self, value):
        if not Product.objects.filter(id=value, status='active').exists():
            raise serializers.ValidationError('Product not found or not available.')
        return value


class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source='product.id', read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product_id', 'product_name', 'unit_price', 'quantity', 'subtotal']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'status', 'total_price', 'created_at',
            'full_name', 'email', 'phone', 'address', 'city', 'postal_code', 'country',
            'items',
        ]
        read_only_fields = ['id', 'total_price', 'created_at', 'items']


class AdminOrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'status', 'total_price', 'created_at', 'updated_at',
            'user_email', 'user_name',
            'full_name', 'email', 'phone', 'address', 'city', 'postal_code', 'country',
            'items',
        ]
        read_only_fields = [
            'id', 'total_price', 'created_at', 'updated_at',
            'user_email', 'user_name',
            'full_name', 'email', 'phone', 'address', 'city', 'postal_code', 'country',
            'items',
        ]


class CheckoutSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    address = serializers.CharField(max_length=255)
    city = serializers.CharField(max_length=100)
    postal_code = serializers.CharField(max_length=20)
    country = serializers.CharField(max_length=100)

    def validate(self, data):
        user = self.context['request'].user
        cart_items = (
            CartItem.objects
            .filter(cart__user=user)
            .select_related('product')
        )

        if not cart_items.exists():
            raise serializers.ValidationError('Your cart is empty.')

        errors = []
        for item in cart_items:
            product = item.product
            if product.status != 'active':
                errors.append(f'"{product.name}" is no longer available.')
            elif product.stock < item.quantity:
                errors.append(f'Not enough stock for "{product.name}" (available: {product.stock}).')

        if errors:
            raise serializers.ValidationError(errors)

        self._cart_items = cart_items
        return data

    def create(self, validated_data):
        user = self.context['request'].user

        with transaction.atomic():
            cart_items = (
                CartItem.objects
                .filter(cart__user=user)
                .select_related('product')
                .select_for_update()
            )

            order = Order.objects.create(user=user, **validated_data)
            total_price = Decimal('0.00')
            order_items = []

            for item in cart_items:
                product = item.product
                if product.status != 'active' or product.stock < item.quantity:
                    raise ValidationError(
                        f'"{product.name}" is no longer available or out of stock.'
                    )
                unit_price = product.final_price
                order_items.append(OrderItem(
                    order=order,
                    product=product,
                    product_name=product.name,
                    unit_price=unit_price,
                    quantity=item.quantity,
                ))
                total_price += unit_price * item.quantity
                product.stock -= item.quantity
                product.save(update_fields=['stock', 'updated_at'])

            OrderItem.objects.bulk_create(order_items)
            order.total_price = total_price
            order.save(update_fields=['total_price'])
            Cart.objects.filter(user=user).first().items.all().delete()

        return order

