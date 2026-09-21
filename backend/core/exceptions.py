"""Consistent API error envelope: { detail, code, errors }."""
from __future__ import annotations

from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None
    data = response.data
    if isinstance(data, dict) and "detail" not in data and "code" not in data:
        response.data = {"detail": "Validation failed.", "code": "validation_error", "errors": data}
    elif isinstance(data, dict) and "detail" in data and "code" not in data:
        response.data = {"detail": data.get("detail"), "code": "error", "errors": {}}
    return response
