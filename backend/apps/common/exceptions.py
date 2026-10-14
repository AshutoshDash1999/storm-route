"""
Error types and the DRF exception handler.

Every error response has the same shape:

    {"error": {"code": "validation_error", "message": "...", "fields": {"origin": ["..."]}}}

`fields` is present only for input errors, keyed by request field name.
"""

import logging

from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_handler

logger = logging.getLogger('stormroute')


class ApiError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'bad_request'
    default_detail = 'Bad request.'

    def __init__(self, message: str | None = None, *, code: str | None = None, fields: dict | None = None,
                 status_code: int | None = None):
        super().__init__(message or self.default_detail, code or self.default_code)
        self.error_code = code or self.default_code
        self.fields = fields
        if status_code:
            self.status_code = status_code


class NotFound(ApiError):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = 'not_found'
    default_detail = 'Not found.'


# Provider errors are raised by adapters and are not HTTP-aware. The analysis
# service catches them to fall back or degrade; anything that escapes is mapped
# to a 5xx by `handler`.

class ProviderError(Exception):
    code = 'provider_error'
    http_status = status.HTTP_502_BAD_GATEWAY

    def __init__(self, provider: str, message: str):
        super().__init__(f'{provider}: {message}')
        self.provider = provider
        self.message = message


class ProviderTimeout(ProviderError):
    code = 'provider_timeout'
    http_status = status.HTTP_504_GATEWAY_TIMEOUT


class ProviderRateLimited(ProviderError):
    code = 'provider_rate_limited'
    http_status = status.HTTP_503_SERVICE_UNAVAILABLE


class ProviderUnavailable(ProviderError):
    code = 'provider_unavailable'
    http_status = status.HTTP_503_SERVICE_UNAVAILABLE


class ProviderBadResponse(ProviderError):
    code = 'provider_bad_response'


class NoRouteFound(ProviderError):
    """The provider answered, but there is no drivable route between the points."""
    code = 'no_route'
    http_status = status.HTTP_422_UNPROCESSABLE_ENTITY

    def __init__(self, provider: str, message: str, field: str = 'destination'):
        super().__init__(provider, message)
        self.field = field


def _body(code: str, message: str, fields: dict | None = None) -> dict:
    error = {'code': code, 'message': message}
    if fields:
        error['fields'] = fields
    return {'error': error}


def _flatten(detail) -> dict[str, list[str]]:
    if isinstance(detail, dict):
        out = {}
        for key, value in detail.items():
            if isinstance(value, dict):
                # Nested serializer (e.g. origin.lat) collapses onto the parent field
                out[key] = [msg for msgs in _flatten(value).values() for msg in msgs]
            else:
                out[key] = [str(v) for v in (value if isinstance(value, list) else [value])]
        return out
    return {'non_field_errors': [str(v) for v in (detail if isinstance(detail, list) else [detail])]}


def handler(exc, context):
    if isinstance(exc, ValidationError):
        fields = _flatten(exc.detail)
        first = next(iter(fields.values()), ['Invalid input.'])[0]
        return Response(_body('validation_error', first, fields), status=status.HTTP_400_BAD_REQUEST)

    if isinstance(exc, ApiError):
        return Response(_body(exc.error_code, str(exc.detail), exc.fields), status=exc.status_code)

    if isinstance(exc, NoRouteFound):
        return Response(_body(exc.code, exc.message, {exc.field: [exc.message]}), status=exc.http_status)

    if isinstance(exc, ProviderError):
        logger.warning('Provider failure escaped to the API: %s', exc)
        return Response(_body(exc.code, f'{exc.provider} is unavailable right now. Try again shortly.'),
                        status=exc.http_status)

    if isinstance(exc, Http404):
        return Response(_body('not_found', 'Not found.'), status=status.HTTP_404_NOT_FOUND)

    response = drf_handler(exc, context)
    if response is not None:
        detail = response.data.get('detail', 'Request failed.') if isinstance(response.data, dict) else response.data
        code = getattr(detail, 'code', None) or 'error'
        response.data = _body(str(code), str(detail))
        return response

    logger.exception('Unhandled error', exc_info=exc)
    return Response(_body('server_error', 'Something went wrong on our side.'),
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)
