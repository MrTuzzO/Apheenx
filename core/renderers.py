from rest_framework.renderers import JSONRenderer


class StandardRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get("response")
        status_code = response.status_code

        # already wrapped — pass through as-is
        if isinstance(data, dict) and "status" in data and "code" in data:
            return super().render(data, accepted_media_type, renderer_context)

        # if response is just {"detail": "some message"}, lift it to message field
        if isinstance(data, dict) and "detail" in data and len(data) == 1:
            wrapped = {
                "status": "success",
                "code": status_code,
                "message": data["detail"],
                "data": None,
            }
        else:
            wrapped = {
                "status": "success",
                "code": status_code,
                "message": "OK",
                "data": data,
            }

        return super().render(wrapped, accepted_media_type, renderer_context)