from django.urls import path
from .views import *

urlpatterns = [
    # Physical product orders
    path('orders/', UserOrderListView.as_view()),
    path('orders/create/', CreateOrderView.as_view()),
    path('orders/<int:order_id>/', OrderDetailView.as_view()),
    path('orders/<int:order_id>/capture/', CapturePaymentView.as_view()),
    path('orders/<int:order_id>/status/', UpdateOrderStatusView.as_view()),
    path('webhook/paypal/', PayPalWebhookView.as_view()),

    # Video orders 
    path('video-orders/', UserVideoOrderListView.as_view()),
    path('video-orders/create/', CreateVideoOrderView.as_view()),
    path('video-orders/<int:order_id>/capture/', CaptureVideoPaymentView.as_view()),
]