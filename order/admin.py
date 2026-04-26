from django.contrib import admin
from order.models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_name', 'unit_price', 'quantity')
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'order_status', 'payment_status', 'total_price', 'created_at')
    list_filter = ('order_status', 'payment_status', 'created_at')
    search_fields = ('user__email',)
    inlines = [OrderItemInline]
