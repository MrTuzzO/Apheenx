from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            "status": "success",
            "code": 200,
            "message": "OK",
            "data": data,
            "errors": None,
            "meta": {
                "count": self.page.paginator.count,
                "page": self.page.number,
                "page_size": self.get_page_size(self.request),
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "total_pages": self.page.paginator.num_pages,
            },
        })

    def get_paginated_response_schema(self, schema):
        # Tells drf-spectacular the shape of paginated responses
        return {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "code": {"type": "integer"},
                "message": {"type": "string"},
                "data": schema,
                "errors": {"type": "object", "nullable": True},
                "meta": {
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer"},
                        "page": {"type": "integer"},
                        "page_size": {"type": "integer"},
                        "next": {"type": "string", "nullable": True},
                        "previous": {"type": "string", "nullable": True},
                        "total_pages": {"type": "integer"},
                    },
                },
            },
        }