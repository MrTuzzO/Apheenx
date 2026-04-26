from django.db.models import Sum, Count
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser
from order.models import Order
from video.models import VideoOrder, Video

User = get_user_model()


class DashboardStatsView(APIView):
    permission_classes = [AllowAny]
    # permission_classes = [IsAdminUser]
    

    def get(self, request):
        total_users = User.objects.count()

        product_stats = Order.objects.filter(
            payment_status='captured'
        ).aggregate(
            total_product_orders=Count('id'),
            total_product_revenue=Sum('total_price'),
        )

        video_stats = VideoOrder.objects.filter(
            payment_status='captured'
        ).aggregate(
            total_video_orders=Count('id'),
            total_video_revenue=Sum('amount'),
        )

        total_videos = Video.objects.count()
        published_videos = Video.objects.filter(status='published').count()

        total_orders = (
            (product_stats['total_product_orders'] or 0) +
            (video_stats['total_video_orders'] or 0)
        )
        total_revenue = (
            (product_stats['total_product_revenue'] or 0) +
            (video_stats['total_video_revenue'] or 0)
        )

        return Response({
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