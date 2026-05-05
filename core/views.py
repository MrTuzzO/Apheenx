from decimal import Decimal
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from order.models import Order
from video.models import VideoOrder, Video
from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet
from core.response import SuccessResponse
from rest_framework.permissions import AllowAny
from core.models import BusinessSetting
from core.serializers import BusinessSettingSerializer
from django.core.cache import cache
from user.permission import IsAdmin
from rest_framework.response import Response

User = get_user_model()

# For Custom Exception Handling, Error Responses
class BaseModelViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return SuccessResponse(
            data=serializer.data,
            message="Created successfully.",
            code=201,
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return SuccessResponse(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return SuccessResponse(data=serializer.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return SuccessResponse(data=serializer.data, message="Updated successfully.")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return SuccessResponse(data=None, message="Deleted successfully.", code=204)


# Utility functions for dashboard stats
def _month_start(value):
    return value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _add_months(value, months):
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return value.replace(year=year, month=month)


def _money(value):
    return float(value or Decimal('0'))


def _integer(value):
    return int(value or 0)


class BusinessSettingView(APIView):

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAdmin()]

    def get(self, request):
        obj = cache.get('business_setting')
        if obj is None:
            obj = BusinessSetting.objects.first()
            cache.set('business_setting', obj, timeout=60*60*24)  # 1 day
        return Response(BusinessSettingSerializer(obj).data if obj else {})

    def post(self, request):
        if BusinessSetting.objects.exists():
            return Response({"detail": "Already exists. Use PATCH to update."}, status=400)
        serializer = BusinessSettingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        cache.delete('business_setting')
        return Response(serializer.data, status=201)

    def patch(self, request):
        obj = BusinessSetting.objects.first()
        if not obj:
            return Response({"detail": "Not found. Use POST to create."}, status=404)
        serializer = BusinessSettingSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        cache.delete('business_setting')
        return Response(serializer.data)


class DashboardStatsView(APIView):
    # permission_classes = [AllowAny]
    permission_classes = [IsAdminUser]
    

    @extend_schema(request=None, responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        total_users = User.objects.count()

        product_stats = Order.objects.order_by().filter(
            payment_status='captured'
        ).aggregate(
            total_product_orders=Count('id'),
            total_product_revenue=Sum('total_price'),
        )

        video_stats = VideoOrder.objects.order_by().filter(
            payment_status='captured'
        ).aggregate(
            total_video_orders=Count('id'),
            total_video_revenue=Sum('amount'),
        )

        video_counts = Video.objects.order_by().aggregate(
            total=Count('id'),
            published=Count('id', filter=Q(status='published')),
        )
        total_videos = video_counts['total'] or 0
        published_videos = video_counts['published'] or 0

        total_orders = (
            (product_stats['total_product_orders'] or 0) +
            (video_stats['total_video_orders'] or 0)
        )
        total_revenue = (
            (product_stats['total_product_revenue'] or 0) +
            (video_stats['total_video_revenue'] or 0)
        )

        return SuccessResponse({
            "users": {
                "total": total_users,
            },
            "orders": {
                "total": total_orders,
                "product_orders": product_stats['total_product_orders'] or 0,
                "video_orders": video_stats['total_video_orders'] or 0,
            },
            "revenue": {
                "total": total_revenue,
                "from_products": product_stats['total_product_revenue'] or 0,
                "from_videos": video_stats['total_video_revenue'] or 0,
            },
            "videos": {
                "total": total_videos,
                "published": published_videos,
                "draft": total_videos - published_videos,
            },
        })


class DashboardChartsView(APIView):
    # permission_classes = [AllowAny]
    permission_classes = [IsAdminUser]

    @extend_schema(
        request=None,
        parameters=[
            OpenApiParameter(
                name="months",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Number of months to include in sales trend. Min 1, max 24.",
            ),
            OpenApiParameter(
                name="video_metric",
                type=str,
                location=OpenApiParameter.QUERY,
                enum=["views", "revenue", "orders"],
                description="Metric for video performance chart.",
            ),
            OpenApiParameter(
                name="limit",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Maximum video categories to return. Min 1, max 20.",
            ),
        ],
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request):
        months_count = self._get_months_count(request)
        sales_trend = self._get_sales_trend(months_count)
        video_performance = self._get_video_performance(request)

        return SuccessResponse({
            "sales_trend": sales_trend,
            "video_performance": video_performance,
        })

    def _get_months_count(self, request):
        try:
            months_count = int(request.query_params.get('months', 6))
        except (TypeError, ValueError):
            months_count = 6
        return min(max(months_count, 1), 24)

    def _get_sales_trend(self, months_count):
        current_month = _month_start(timezone.now())
        start_month = _add_months(current_month, -(months_count - 1))
        end_month = _add_months(current_month, 1)

        month_keys = [
            _add_months(start_month, index)
            for index in range(months_count)
        ]
        revenue_by_month = {
            month.strftime('%Y-%m'): Decimal('0')
            for month in month_keys
        }

        product_revenue = Order.objects.order_by().filter(
            payment_status='captured',
            created_at__gte=start_month,
            created_at__lt=end_month,
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            revenue=Sum('total_price')
        )

        video_revenue = VideoOrder.objects.order_by().filter(
            payment_status='captured',
            created_at__gte=start_month,
            created_at__lt=end_month,
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            revenue=Sum('amount')
        )

        for row in product_revenue:
            revenue_by_month[row['month'].strftime('%Y-%m')] += row['revenue'] or Decimal('0')

        for row in video_revenue:
            revenue_by_month[row['month'].strftime('%Y-%m')] += row['revenue'] or Decimal('0')

        return {
            "labels": [month.strftime('%b') for month in month_keys],
            "values": [_money(revenue_by_month[month.strftime('%Y-%m')]) for month in month_keys],
        }

    def _get_video_performance(self, request):
        metric = request.query_params.get('video_metric', 'views')
        if metric not in {'views', 'revenue', 'orders'}:
            metric = 'views'

        limit = self._get_limit(request)

        if metric == 'revenue':
            rows = VideoOrder.objects.order_by().filter(
                payment_status='captured'
            ).values(
                'video__category__name'
            ).annotate(
                value=Sum('amount')
            ).order_by('-value')[:limit]
        elif metric == 'orders':
            rows = VideoOrder.objects.order_by().filter(
                payment_status='captured'
            ).values(
                'video__category__name'
            ).annotate(
                value=Count('id')
            ).order_by('-value')[:limit]
        else:
            rows = Video.objects.order_by().values(
                'category__name'
            ).annotate(
                value=Sum('views_count')
            ).order_by('-value')[:limit]

        return {
            "metric": metric,
            "labels": [
                row.get('category__name') or row.get('video__category__name')
                for row in rows
            ],
            "values": [
                _money(row['value']) if metric == 'revenue' else _integer(row['value'])
                for row in rows
            ],
        }

    def _get_limit(self, request):
        try:
            limit = int(request.query_params.get('limit', 5))
        except (TypeError, ValueError):
            limit = 5
        return min(max(limit, 1), 20)
