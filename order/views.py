import json
import logging
from django.db import models, transaction
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from product.models import Product
from user.permission import IsAdmin, IsAdminOrReadOnly
from .models import ORDER_STATUS_CHOICES, PAYMENT_STATUS_CHOICES, Order, OrderItem
from .serializers import *
from .paypal_service import create_paypal_order, capture_paypal_order, create_paypal_video_order
from .paypal_client import verify_paypal_webhook, paypal_request
from video.models import Video, VideoOrder
from rest_framework.renderers import JSONRenderer

logger = logging.getLogger(__name__)


class CreateOrderView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=CreateOrderSerializer, responses={201: OpenApiTypes.OBJECT})
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
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: OpenApiTypes.OBJECT})
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
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OrderSerializer})
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

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="payment_status",
                type=str,
                location=OpenApiParameter.QUERY,
                enum=[choice[0] for choice in PAYMENT_STATUS_CHOICES],
            ),
            OpenApiParameter(
                name="order_status",
                type=str,
                location=OpenApiParameter.QUERY,
                enum=[choice[0] for choice in ORDER_STATUS_CHOICES],
            ),
        ],
        responses={200: OrderSerializer(many=True)},
    )
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
    permission_classes = [IsAdmin]

    @extend_schema(request=UpdateOrderStatusSerializer, responses={200: OpenApiTypes.OBJECT})
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


# --------------------------------------------------------------------
# Video orders (no shipping, no line items)---------------------------
# --------------------------------------------------------------------

class CreateVideoOrderView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=CreateVideoOrderSerializer, responses={201: OpenApiTypes.OBJECT})
    def post(self, request):
        serializer = CreateVideoOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        video = get_object_or_404(Video, id=serializer.validated_data['video_id'], status='published')

        existing = VideoOrder.objects.filter(user=request.user, video=video).first()
        if existing:
            if existing.is_paid:
                return Response(
                    {"detail": "You already own this video."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Pending order exists — return it so frontend can resume
            return Response({
                "detail": "You have a pending order. Complete your payment.",
                "order_id": existing.id,
                "paypal_order_id": existing.paypal_order_id,
                "amount": str(existing.amount),
            }, status=status.HTTP_200_OK)

        order = VideoOrder.objects.create(
            user=request.user,
            video=video,
            amount=video.price,
        )

        try:
            paypal_order_id, approval_url = create_paypal_video_order(order)
        except Exception as e:
            order.payment_status = 'failed'
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
            "amount": str(video.price),
            "currency": "USD",
        }, status=status.HTTP_201_CREATED)


class CaptureVideoPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: OpenApiTypes.OBJECT})
    def post(self, request, order_id):
        order = get_object_or_404(VideoOrder, id=order_id, user=request.user)

        if order.payment_status == 'captured':
            return Response(
                {"detail": "Already paid.", "order": VideoOrderSerializer(order, context={'request': request}).data},
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
                {"detail": f"PayPal returned: {result.get('status')}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            order.payment_status = 'captured'
            order.save()
            Video.objects.filter(id=order.video_id).update(
                income=models.F('income') + order.amount
            )

        return Response({
            "detail": "Payment successful. You can now watch the video.",
            "order": VideoOrderSerializer(order, context={'request': request}).data,
        })


class UserVideoOrderListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: VideoOrderSerializer(many=True)})
    def get(self, request):
        orders = VideoOrder.objects.filter(
            user=request.user,
            payment_status='captured'
        ).select_related('video')
        return Response(VideoOrderSerializer(orders, many=True, context={'request': request}).data)


@method_decorator(csrf_exempt, name='dispatch')
class PayPalWebhookView(APIView):
    authentication_classes = []
    permission_classes = []
    renderer_classes = [JSONRenderer]

    def post(self, request):
        if not verify_paypal_webhook(request.headers, request.body):
            logger.warning("PayPal webhook rejected: verification failed.")
            return Response({"status": "ignored"}, status=status.HTTP_200_OK)

        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            logger.warning("PayPal webhook rejected: invalid JSON body.")
            return Response({"status": "ignored"}, status=status.HTTP_200_OK)

        event_type = payload.get('event_type')
        logger.info("PayPal webhook received: event_type=%s", event_type)

        if event_type == 'PAYMENT.CAPTURE.COMPLETED':
            resolved = self._resolve_reference_id(payload)
            if not resolved:
                logger.warning(
                    "PayPal webhook: could not resolve reference_id from payload."
                )
                return Response({"status": "ok"})

            order_type, order_id = resolved

            if order_type == 'video':
                self._fulfill_video_order(order_id)
            elif order_type == 'product':
                self._fulfill_product_order(order_id)
            else:
                logger.warning(
                    "PayPal webhook: unknown order_type '%s' for resolved order id=%s.",
                    order_type,
                    order_id,
                )

        return Response({"status": "ok"})

    def _resolve_reference_id(self, payload: dict):
        try:
            # Some webhook payloads include purchase_units.reference_id directly.
            direct_reference_id = payload['resource']['purchase_units'][0]['reference_id']
            order_type, order_id_str = direct_reference_id.split('_', 1)
            return order_type, int(order_id_str)
        except (KeyError, IndexError, TypeError, ValueError):
            pass

        try:
            paypal_order_id = payload['resource']['supplementary_data']['related_ids']['order_id']
        except (KeyError, TypeError):
            return None

        try:
            order_result = paypal_request("GET", f"/v2/checkout/orders/{paypal_order_id}")
            reference_id = order_result['purchase_units'][0]['reference_id']
            order_type, order_id_str = reference_id.split('_', 1)
            return order_type, int(order_id_str)
        except Exception:
            logger.exception(
                "PayPal webhook: failed to fetch order details for order_id=%s",
                paypal_order_id,
            )
            return None

    def _fulfill_video_order(self, order_id: int) -> None:
        try:
            order = VideoOrder.objects.get(id=order_id)
            if not order.is_paid:
                with transaction.atomic():
                    order.payment_status = 'captured'
                    order.save()
                    Video.objects.filter(id=order.video_id).update(
                        income=models.F('income') + order.amount
                    )
                logger.info("PayPal webhook: fulfilled VideoOrder id=%s", order_id)
            else:
                logger.info(
                    "PayPal webhook: VideoOrder id=%s already paid, skipping.", order_id
                )
        except VideoOrder.DoesNotExist:
            logger.warning("PayPal webhook: VideoOrder id=%s not found.", order_id)

    def _fulfill_product_order(self, order_id: int) -> None:
        try:
            order = Order.objects.get(id=order_id)
            if order.payment_status != 'captured':
                with transaction.atomic():
                    order.payment_status = 'captured'
                    order.order_status = 'processing'
                    order.save()
                    for item in order.items.select_related('product'):
                        Product.objects.filter(id=item.product_id).update(
                            stock=models.F('stock') - item.quantity
                        )
                logger.info("PayPal webhook: fulfilled Order id=%s", order_id)
            else:
                logger.info(
                    "PayPal webhook: Order id=%s already captured, skipping.", order_id
                )
        except Order.DoesNotExist:
            logger.warning("PayPal webhook: Order id=%s not found.", order_id)