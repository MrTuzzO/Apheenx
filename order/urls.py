from django.urls import path
from .views import (
    CreateOrderView,
    CapturePaymentView,
    OrderDetailView,
    UserOrderListView,
    UpdateOrderStatusView,
    PayPalWebhookView,
)

urlpatterns = [
    path('orders/', UserOrderListView.as_view()),
    path('orders/create/', CreateOrderView.as_view()),
    path('orders/<int:order_id>/', OrderDetailView.as_view()),
    path('orders/<int:order_id>/capture/', CapturePaymentView.as_view()),
    path('orders/<int:order_id>/status/', UpdateOrderStatusView.as_view()),
    path('webhook/paypal/', PayPalWebhookView.as_view()),
]