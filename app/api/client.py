"""Reusable HTTP client for Mercado Publico public API."""

from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests
from requests import Response, Session

from app.config import Settings, get_settings, require_ticket

from . import endpoints
from .exceptions import (
    MercadoPublicoEmptyResponseError,
    MercadoPublicoHTTPError,
    MercadoPublicoJSONError,
    MercadoPublicoRequestError,
)


class MercadoPublicoAPIClient:
    """HTTP client with retries, timeout handling and defensive JSON parsing."""

    def __init__(
        self,
        settings: Settings | None = None,
        session: Session | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.session = session or requests.Session()
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.ticket = require_ticket(self.settings)

    def get_licitaciones_today(self, estado: str | None = None) -> dict[str, Any]:
        """Fetch current day licitations, optionally filtered by status."""
        spec = endpoints.licitaciones_today(estado=estado)
        return self._get(spec.resource, params=spec.params)
  
    def get_licitaciones_by_date(
        self,
        target_date: str,
        estado: str | None = None,
    ) -> dict[str, Any]:
        """Fetch licitations for a given date in ISO or ddmmaaaa format."""
        spec = endpoints.licitaciones_by_date(target_date=target_date, estado=estado)
        return self._get(spec.resource, params=spec.params)

    def get_licitacion_by_code(self, codigo: str) -> dict[str, Any]:
        """Fetch a licitation by its Mercado Publico code."""
        spec = endpoints.licitacion_by_code(codigo=codigo)
        return self._get(spec.resource, params=spec.params)

    def get_ordenes_compra_by_date(
        self,
        target_date: str,
        estado: str | None = None,
    ) -> dict[str, Any]:
        """Prepared method for future purchase order support."""
        spec = endpoints.ordenes_compra_by_date(target_date=target_date, estado=estado)
        return self._get(spec.resource, params=spec.params)

    def _get(self, resource: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a GET request against a Mercado Publico resource."""
        request_params = {"ticket": self.ticket}
        if params:
            request_params.update(params)
        return self._request("GET", resource=resource, params=request_params)

    def _request(
        self,
        method: str,
        resource: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.settings.mp_base_url}/{resource.lstrip('/')}"
        retries = self.settings.max_retries

        for attempt in range(1, retries + 1):
            try:
                self.logger.info(
                    "Mercado Publico request",
                    extra={
                        "method": method,
                        "url": url,
                        "attempt": attempt,
                        "params": _without_ticket(params),
                    },
                )
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    timeout=self.settings.request_timeout,
                )
                self._raise_for_status(response)
                return self._parse_json(response)
            except (
                requests.RequestException,
                MercadoPublicoHTTPError,
                MercadoPublicoJSONError,
                MercadoPublicoEmptyResponseError,
            ) as exc:
                is_last_attempt = attempt == retries
                self.logger.warning(
                    "Mercado Publico request failed",
                    extra={
                        "url": url,
                        "attempt": attempt,
                        "max_retries": retries,
                        "error": str(exc),
                    },
                )
                if is_last_attempt:
                    raise MercadoPublicoRequestError(
                        f"Request failed after {retries} attempts for {url}: {exc}"
                    ) from exc

                time.sleep(self.settings.retry_backoff_seconds * attempt)

        raise MercadoPublicoRequestError(f"Unexpected request flow for {url}")

    def _raise_for_status(self, response: Response) -> None:
        if response.status_code >= 400:
            raise MercadoPublicoHTTPError(
                f"HTTP {response.status_code} returned by Mercado Publico API for {_safe_url(response.url)}"
            )

    def _parse_json(self, response: Response) -> dict[str, Any]:
        if not response.text or not response.text.strip():
            raise MercadoPublicoEmptyResponseError(f"Empty response received from {_safe_url(response.url)}")

        try:
            payload = response.json()
        except ValueError as exc:
            raise MercadoPublicoJSONError(f"Invalid JSON received from {_safe_url(response.url)}") from exc

        if not isinstance(payload, dict):
            raise MercadoPublicoJSONError(
                f"Unexpected JSON payload type {type(payload).__name__} from {_safe_url(response.url)}"
            )

        return payload


def _without_ticket(params: dict[str, Any] | None) -> dict[str, Any]:
    """Return the request parameters without the access ticket, for logging."""

    return {key: value for key, value in (params or {}).items() if key != "ticket"}


def _safe_url(url: str) -> str:
    """Return the URL without the ticket query parameter, for logs and error messages."""

    parts = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key != "ticket"]
    return urlunsplit(parts._replace(query=urlencode(query)))
