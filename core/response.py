from rest_framework.response import Response


class SuccessResponse(Response):
    def __init__(self, data=None, message="OK", code=200, **kwargs):
        payload = {
            "status": "success",
            "code": code,
            "message": message,
            "data": data,
        }
        super().__init__(data=payload, status=code, **kwargs)


class ErrorResponse(Response):
    def __init__(self, message="An error occurred", errors=None, code=400, **kwargs):
        payload = {
            "status": "error",
            "code": code,
            "message": message,
            "data": None,
        }
        super().__init__(data=payload, status=code, **kwargs)