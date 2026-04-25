from django.db import models, transaction
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
import json
from product.models import Product
from .models import Order, OrderItem
from .serializers import (
    OrderSerializer,
    CreateOrderSerializer,
    UpdateOrderStatusSerializer,
)
from .paypal_service import create_paypal_order, capture_paypal_order
from .paypal_client import verify_paypal_webhook


class CreateOrderView(APIView):
    """
    POST /api/payments/orders/
    Creates order + OrderItems, then creates PayPal order.
    Returns approval_url for frontend to redirect user.

    Request body:
        {
        "full_name": "John Doe",
        "email": "john@example.com",
        "phone": "+1-555-1234",
        "address": "123 Main St",
        "city": "New York",
        "state": "FL",
        "postal_code": "10001",
        "country": "USA",
        "items": [
            {"product_id": 1, "quantity": 2},
            {"product_id": 4, "quantity": 1}
        ]
        }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        cart_items = data['items']
        product_ids = [i['product_id'] for i in cart_items]
        products = Product.objects.filter(id__in=product_ids, status='active')
        product_map = {p.id: p for p in products}

        errors = {}
        for item in cart_items:
            pid = item['product_id']
            qty = item['quantity']
            if pid not in product_map:
                errors[str(pid)] = "Product not found or inactive."
            elif product_map[pid].stock < qty:
                errors[str(pid)] = f"Only {product_map[pid].stock} in stock."

        if errors:
            return Response(
                {"detail": "Some items have issues.", "errors": errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        total_price = round(
            sum(
                product_map[i['product_id']].final_price * i['quantity']
                for i in cart_items
            ), 2
        )

        with transaction.atomic():
            order = Order.objects.create(
                user=request.user,
                full_name=data['full_name'],
                email=data['email'],
                phone=data['phone'],
                address=data['address'],
                city=data['city'],
                state=data['state'],
                postal_code=data['postal_code'],
                country=data['country'],
                total_price=total_price,
            )

            OrderItem.objects.bulk_create([
                OrderItem(
                    order=order,
                    product=product_map[i['product_id']],
                    quantity=i['quantity'],
                    unit_price=product_map[i['product_id']].final_price,
                )
                for i in cart_items
            ])

        try:
            paypal_order_id, approval_url = create_paypal_order(order)
        except Exception as e:
            order.payment_status = 'failed'
            order.order_status = 'cancelled'
            order.save()
            return Response(
                {"detail": f"PayPal error: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY
            )

        order.paypal_order_id = paypal_order_id
        order.save()

        return Response({
            "order_id": order.id,
            "paypal_order_id": paypal_order_id,
            "approval_url": approval_url,
            "total_price": str(total_price),
            "items": [
                {
                    "product_id": i['product_id'],
                    "product_name": product_map[i['product_id']].name,
                    "quantity": i['quantity'],
                    "unit_price": str(product_map[i['product_id']].final_price),
                    "subtotal": str(
                        round(product_map[i['product_id']].final_price * i['quantity'], 2)
                    ),
                }
                for i in cart_items
            ],
        }, status=status.HTTP_201_CREATED)


class CapturePaymentView(APIView):
    """
    POST /api/payments/orders/{order_id}/capture/
    Call after user approves on PayPal and is redirected back.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, user=request.user)

        if order.payment_status == 'captured':
            return Response(
                {"detail": "Already captured.", "order": OrderSerializer(order).data},
                status=status.HTTP_200_OK
            )
        if order.payment_status == 'failed':
            return Response(
                {"detail": "Order failed. Please create a new order."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = capture_paypal_order(order.paypal_order_id)
        except Exception as e:
            order.payment_status = 'failed'
            order.save()
            return Response(
                {"detail": f"Capture failed: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY
            )

        if result.get('status') != 'COMPLETED':
            order.payment_status = 'failed'
            order.save()
            return Response(
                {"detail": f"PayPal returned: {result.get('status')}. Not completed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Payment successful — fulfill order
        with transaction.atomic():
            order.payment_status = 'captured'
            order.order_status = 'processing'
            order.save()

            # Decrement stock
            for item in order.items.select_related('product'):
                Product.objects.filter(id=item.product_id).update(
                    stock=models.F('stock') - item.quantity
                )

        return Response({
            "detail": "Payment successful.",
            "order": OrderSerializer(order).data,
        })


class OrderDetailView(APIView):
    """GET /api/payments/orders/{order_id}/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        order = get_object_or_404(
            Order.objects.prefetch_related('items__product'),
            id=order_id,
            user=request.user
        )
        return Response(OrderSerializer(order).data)


class UserOrderListView(APIView):
    """
    GET /api/payments/orders/
    Filters: ?payment_status=captured  ?order_status=shipped
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(
            user=request.user
        ).prefetch_related('items__product')

        if request.query_params.get('payment_status'):
            orders = orders.filter(payment_status=request.query_params['payment_status'])
        if request.query_params.get('order_status'):
            orders = orders.filter(order_status=request.query_params['order_status'])

        return Response(OrderSerializer(orders, many=True).data)


class UpdateOrderStatusView(APIView):
    """
    PATCH /api/payments/orders/{order_id}/status/
    Staff only.
    Body: { "order_status": "shipped" }
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, order_id):
        if not request.user.is_staff:
            return Response(
                {"detail": "Not authorized."},
                status=status.HTTP_403_FORBIDDEN
            )

        order = get_object_or_404(Order, id=order_id)
        serializer = UpdateOrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if not order.is_paid and data['order_status'] != 'cancelled':
            return Response(
                {"detail": "Cannot update fulfillment status of an unpaid order."},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.order_status = data['order_status']
        order.save()

        return Response({
            "detail": "Status updated.",
            "order": OrderSerializer(order).data,
        })


@method_decorator(csrf_exempt, name='dispatch')
class PayPalWebhookView(APIView):   
    """
    POST /api/payments/webhook/paypal/
    Safety net — fulfills order if user closes browser after paying.
    Register this URL in PayPal Developer Dashboard.
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # Verify the webhook is genuinely from PayPal
        if not verify_paypal_webhook(request.headers, request.body):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if payload.get('event_type') == 'PAYMENT.CAPTURE.COMPLETED':
            try:
                reference_id = (
                    payload['resource']
                    ['purchase_units'][0]
                    ['reference_id']
                )
                order = Order.objects.get(id=int(reference_id))

                if order.payment_status != 'captured':
                    with transaction.atomic():
                        order.payment_status = 'captured'
                        order.order_status = 'processing'
                        order.save()

                        for item in order.items.select_related('product'):
                            Product.objects.filter(id=item.product_id).update(
                                stock=models.F('stock') - item.quantity
                            )

            except (Order.DoesNotExist, KeyError, IndexError, TypeError):
                pass

        return Response({"status": "ok"})