from django.conf import settings
from .paypal_client import paypal_request


def create_paypal_order(order) -> tuple[str, str]:
    paypal_items = []
    for item in order.items.select_related('product'):
        paypal_items.append({
            "name": item.product.name[:127],
            "quantity": str(item.quantity),
            "unit_amount": {
                "currency_code": order.currency if hasattr(order, 'currency') else "USD",
                "value": str(item.unit_price),
            },
        })

    currency = "USD"
    purchase_unit = {
        "reference_id": f"product_{order.id}", 
        "description": f"Order #{order.id}",
        "amount": {
            "currency_code": currency,
            "value": str(order.total_price),
            "breakdown": {
                "item_total": {
                    "currency_code": currency,
                    "value": str(order.total_price),
                }
            },
        },
        "items": paypal_items,
        "shipping": {
            "name": {"full_name": order.full_name},
            "address": {
                "address_line_1": order.address,
                "admin_area_1": order.state,
                "admin_area_2": order.city,
                "postal_code": order.postal_code,
                "country_code": order.country_code if hasattr(order, 'country_code') else "US",
            },
        },
    }

    result = paypal_request("POST", "/v2/checkout/orders", {
        "intent": "CAPTURE",
        "purchase_units": [purchase_unit],
        "application_context": {
            "brand_name": "Apheenx",
            "landing_page": "NO_PREFERENCE",
            "user_action": "PAY_NOW",
            "shipping_preference": "SET_PROVIDED_ADDRESS",
            "return_url": f"{settings.FRONTEND_BASE_URL}/payment/success",
            "cancel_url": f"{settings.FRONTEND_BASE_URL}/payment/cancel",
        },
    })

    paypal_order_id = result["id"]
    approval_url = next(
        link["href"] for link in result["links"] if link["rel"] == "approve"
    )
    return paypal_order_id, approval_url


def create_paypal_video_order(order) -> tuple[str, str]:
    result = paypal_request("POST", "/v2/checkout/orders", {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "reference_id": f"video_{order.id}",
                "description": f"Video: {order.video.title[:127]}",
                "amount": {
                    "currency_code": "USD",
                    "value": str(order.amount),
                },
            }
        ],
        "application_context": {
            "brand_name": "Apheenx",
            "landing_page": "NO_PREFERENCE",
            "user_action": "PAY_NOW",
            "shipping_preference": "NO_SHIPPING",
            "return_url": f"{settings.FRONTEND_BASE_URL}/payment/success",
            "cancel_url": f"{settings.FRONTEND_BASE_URL}/payment/cancel",
        },
    })

    paypal_order_id = result["id"]
    approval_url = next(
        link["href"] for link in result["links"] if link["rel"] == "approve"
    )
    return paypal_order_id, approval_url


def capture_paypal_order(paypal_order_id: str) -> dict:
    return paypal_request("POST", f"/v2/checkout/orders/{paypal_order_id}/capture")