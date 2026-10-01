import stripe
from django.conf import settings

# Stripe API Key সেট করা
stripe.api_key = settings.STRIPE_SECRET_KEY

def _build_frontend_payment_url(path: str, order_type: str, order_id: int) -> str:
    base_url = settings.FRONTEND_BASE_URL.rstrip('/')
    return f"{base_url}{path}?order_type={order_type}&order_id={order_id}"

def create_stripe_checkout_session(order, order_type="product"):
    if order_type == "product":
        success_url = _build_frontend_payment_url("/payment/success", "product", order.id)
        cancel_url = _build_frontend_payment_url("/payment/cancel", "product", order.id)
        
        line_items = []
        for item in order.items.all():
            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': item.product.name or item.product_name or "Product"},
                    'unit_amount': int(item.unit_price * 100), # Stripe সেন্টস-এ কাজ করে (100 cents = $1)
                },
                'quantity': item.quantity,
            })
    else: # Video Order
        success_url = _build_frontend_payment_url("/payment/success", "video", order.id)
        cancel_url = _build_frontend_payment_url("/payment/cancel", "video", order.id)
        
        line_items = [{
            'price_data': {
                'currency': 'usd',
                'product_data': {'name': f"Video: {order.video.title}"},
                'unit_amount': int(order.amount * 100),
            },
            'quantity': 1,
        }]

    # Stripe Checkout Session তৈরি
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=line_items,
        mode='payment',
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            'order_type': order_type,
            'order_id': order.id,
        }
    )
    return session.url, session.id