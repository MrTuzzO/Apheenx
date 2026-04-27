from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        response.data = {
            "status": "error",
            "code": response.status_code,
            "message": _extract_message(exc, response.data),
            "data": None,
        }

    return response


def _extract_message(exc, data):
    # ── detail-based: auth, jwt, throttle, permission, 404 ──
    if isinstance(data, dict) and "detail" in data:
        detail = data["detail"]
        if isinstance(detail, list):
            return _clean(detail[0])
        return _clean(detail)

    # ── validation errors: show first error only ──
    if isinstance(exc, ValidationError) and isinstance(data, dict):
        for field, errors in data.items():
            first = _get_first_error(errors)
            if first:
                return first
        return "Validation failed."

    # ── list of errors ──
    if isinstance(data, list) and data:
        return _clean(data[0])

    # ── fallback ──
    return _clean(data) if isinstance(data, str) else "An unexpected error occurred."


def _get_first_error(errors):
    """Recursively gets the first error message from any nesting level."""
    if isinstance(errors, list):
        for item in errors:
            result = _get_first_error(item)
            if result:
                return result

    elif isinstance(errors, dict):
        for value in errors.values():
            result = _get_first_error(value)
            if result:
                return result

    elif errors:
        return _clean(errors)

    return None


def _clean(value):
    return str(value).capitalize()