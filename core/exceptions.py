from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        status_code = response.status_code
        data = response.data

        response.data = {
            "status": "error",
            "code": status_code,
            "message": _extract_message(data),
            "data": None,
        }

    return response


def _extract_message(data):
    if isinstance(data, dict):
        if "detail" in data and len(data) == 1:
            return str(data["detail"])

        messages = []
        for field, errors in data.items():
            if isinstance(errors, list):
                for error in errors:
                    messages.append(str(error))
            elif isinstance(errors, dict):
                for nested_field, nested_errors in errors.items():
                    for error in nested_errors:
                        messages.append(str(error))
            else:
                messages.append(str(errors))

        # capitalize first letter of each message and join
        return " | ".join(m.capitalize() for m in messages)

    elif isinstance(data, list):
        return " | ".join(str(e).capitalize() for e in data)

    return str(data).capitalize()