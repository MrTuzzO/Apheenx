from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.db import transaction
from decimal import Decimal

from order.models import Order, OrderItem
from product.models import Product


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
    class CheckoutItemInputSerializer(serializers.Serializer):
        product_id = serializers.IntegerField(min_value=1)
        quantity = serializers.IntegerField(min_value=1)

    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    address = serializers.CharField(max_length=255)
    city = serializers.CharField(max_length=100)
    postal_code = serializers.CharField(max_length=20)
    country = serializers.CharField(max_length=100)
    items = CheckoutItemInputSerializer(many=True, allow_empty=False, write_only=True)

    def validate(self, data):
        items = data['items']
        product_ids = [item['product_id'] for item in items]

        if len(product_ids) != len(set(product_ids)):
            raise serializers.ValidationError({'items': 'Duplicate products are not allowed.'})

        products = Product.objects.filter(id__in=product_ids).only('id', 'name', 'status', 'stock')
        product_map = {product.id: product for product in products}

        errors = []
        for item in items:
            product = product_map.get(item['product_id'])
            if product is None or product.status != 'active':
                errors.append(f'Product #{item["product_id"]} is not available.')
                continue
            if product.stock < item['quantity']:
                errors.append(f'Not enough stock for "{product.name}" (available: {product.stock}).')

        if errors:
            raise serializers.ValidationError({'items': errors})

        return data

    def create(self, validated_data):
        user = self.context['request'].user
        items_data = validated_data.pop('items')
        product_ids = [item['product_id'] for item in items_data]

        with transaction.atomic():
            products = Product.objects.select_for_update().filter(id__in=product_ids)
            product_map = {product.id: product for product in products}

            order = Order.objects.create(user=user, **validated_data)
            total_price = Decimal('0.00')
            order_items = []

            for item in items_data:
                product = product_map.get(item['product_id'])
                quantity = item['quantity']

                if product is None or product.status != 'active' or product.stock < quantity:
                    raise ValidationError(
                        f'Product #{item["product_id"]} is no longer available or out of stock.'
                    )

                unit_price = product.final_price
                order_items.append(OrderItem(
                    order=order,
                    product=product,
                    product_name=product.name,
                    unit_price=unit_price,
                    quantity=quantity,
                ))
                total_price += unit_price * quantity
                product.stock -= quantity
                product.save(update_fields=['stock', 'updated_at'])

            OrderItem.objects.bulk_create(order_items)
            order.total_price = total_price
            order.save(update_fields=['total_price'])

        return order
