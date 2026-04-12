"""Custom exceptions for the Mercado Publico API client."""

from __future__ import annotations


class MercadoPublicoAPIError(Exception):
    """Base exception for API-related errors."""


class MercadoPublicoHTTPError(MercadoPublicoAPIError):
    """Raised when the API returns an unsuccessful HTTP response."""


class MercadoPublicoEmptyResponseError(MercadoPublicoAPIError):
    """Raised when the API returns an empty body."""


class MercadoPublicoJSONError(MercadoPublicoAPIError):
    """Raised when the response payload cannot be decoded as JSON."""


class MercadoPublicoRequestError(MercadoPublicoAPIError):
    """Raised when a request fails after retries."""
