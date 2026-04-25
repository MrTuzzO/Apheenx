import requests
from django.conf import settings


def get_paypal_access_token() -> str:
    url = (
        "https://api-m.sandbox.paypal.com/v1/oauth2/token"
        if settings.PAYPAL_MODE == "sandbox"
        else "https://api-m.paypal.com/v1/oauth2/token"
    )
    response = requests.post(
        url,
        auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
        data={"grant_type": "client_credentials"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def paypal_request(method: str, endpoint: str, payload: dict = None) -> dict:
    base_url = (
        "https://api-m.sandbox.paypal.com"
        if settings.PAYPAL_MODE == "sandbox"
        else "https://api-m.paypal.com"
    )
    token = get_paypal_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    response = requests.request(
        method,
        f"{base_url}{endpoint}",
        json=payload,
        headers=headers,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def verify_paypal_webhook(request_headers: dict, raw_body: bytes) -> bool:
    """
    Verify a PayPal webhook event by calling PayPal's verification API.
    Returns True if the webhook is authentic, False otherwise.
    """
    webhook_id = getattr(settings, "PAYPAL_WEBHOOK_ID", "")
    if not webhook_id:
        # If no webhook ID configured, skip verification (log a warning in production)
        return True

    payload = {
        "auth_algo": request_headers.get("PAYPAL-AUTH-ALGO", ""),
        "cert_url": request_headers.get("PAYPAL-CERT-URL", ""),
        "transmission_id": request_headers.get("PAYPAL-TRANSMISSION-ID", ""),
        "transmission_sig": request_headers.get("PAYPAL-TRANSMISSION-SIG", ""),
        "transmission_time": request_headers.get("PAYPAL-TRANSMISSION-TIME", ""),
        "webhook_id": webhook_id,
        "webhook_event": raw_body.decode("utf-8"),
    }

    try:
        result = paypal_request("POST", "/v1/notifications/verify-webhook-signature", payload)
        return result.get("verification_status") == "SUCCESS"
    except Exception:
        return False