import logging
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import (
    AuthenticationFailed, NotAuthenticated, PermissionDenied,
    ValidationError, Throttled
)

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom DRF exception handler.

    Converts DRF's varied error formats into a consistent shape:
      {
        "error":  "Human-readable message",
        "code":   "MACHINE_READABLE_CODE",
        "detail": { ... }   (optional — only for validation errors)
      }

    HTTP codes are preserved from DRF defaults.
    Unhandled exceptions become 503 (not 500) to avoid leaking stack traces.

    Register in settings:
      REST_FRAMEWORK = {
          'EXCEPTION_HANDLER': 'debate_app.exceptions.custom_exception_handler',
      }
    """
    # Let DRF handle first — sets response.data and response.status_code
    response = drf_exception_handler(exc, context)

    if response is not None:
        original = response.data

        if isinstance(exc, Throttled):
            wait = exc.wait
            response.data = {
                'error': f'Too many requests. Please wait {int(wait)} seconds.' if wait else 'Too many requests.',
                'code': 'RATE_LIMIT_EXCEEDED',
                'retry_after': int(wait) if wait else None,
            }

        elif isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
            response.data = {
                'error': 'Authentication required.',
                'code': 'AUTHENTICATION_REQUIRED',
            }

        elif isinstance(exc, PermissionDenied):
            response.data = {
                'error': 'You do not have permission to perform this action.',
                'code': 'PERMISSION_DENIED',
            }

        elif isinstance(exc, ValidationError):
            # Flatten validation errors
            if isinstance(original, dict):
                first_field = next(iter(original))
                first_error = original[first_field]
                if isinstance(first_error, list):
                    first_error = first_error[0]
                response.data = {
                    'error': str(first_error),
                    'code': 'VALIDATION_ERROR',
                    'detail': original,
                }
            elif isinstance(original, list):
                response.data = {
                    'error': str(original[0]) if original else 'Validation error',
                    'code': 'VALIDATION_ERROR',
                }
            else:
                response.data = {
                    'error': str(original),
                    'code': 'VALIDATION_ERROR',
                }

        else:
            # Generic DRF error
            if isinstance(original, dict) and 'detail' in original:
                code = getattr(original.get('detail'), 'code', 'ERROR')
                if code:
                    code = str(code).upper()
                response.data = {
                    'error': str(original['detail']),
                    'code': code or 'ERROR',
                }
            else:
                response.data = {
                    'error': str(original),
                    'code': 'ERROR',
                }

    else:
        # Unhandled exception (not a DRF exception)
        # Log the full traceback server-side
        view = context.get('view')
        logger.error(
            f'Unhandled exception in {view.__class__.__name__ if view else "unknown view"}: '
            f'{exc}',
            exc_info=True,
        )
        response = Response(
            {
                'error': 'Service temporarily unavailable. Please try again.',
                'code': 'INTERNAL_ERROR',
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
        return response