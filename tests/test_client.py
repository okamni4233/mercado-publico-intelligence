from __future__ import annotations

import json
from typing import Any

import pytest
import requests

from app.api.client import MercadoPublicoAPIClient
from app.api.exceptions import MercadoPublicoRequestError
from app.config import Settings


class FakeResponse:
    def __init__(self, status_code: int = 200, text: str = '{"Cantidad": 0, "Listado": []}') -> None:
        self.status_code = status_code
        self.text = text
        self.url = "https://api.example.test/licitaciones.json"

    def json(self) -> Any:
        return json.loads(self.text)


class FakeSession:
    """Session double that replays queued responses and records each call."""

    def __init__(self, *responses: FakeResponse | Exception) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def request(self, **kwargs: Any) -> FakeResponse:
        self.calls.append(kwargs)
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _settings(ticket: str = "ticket-de-prueba", max_retries: int = 3) -> Settings:
    return Settings.model_validate(
        {
            "MP_TICKET": ticket,
            "MP_BASE_URL": "https://api.example.test/",
            "REQUEST_TIMEOUT": 7,
            "MAX_RETRIES": max_retries,
            "RETRY_BACKOFF_SECONDS": 0,
        }
    )


def _client(session: FakeSession, **settings_kwargs: Any) -> MercadoPublicoAPIClient:
    return MercadoPublicoAPIClient(settings=_settings(**settings_kwargs), session=session)  # type: ignore[arg-type]


def test_client_requires_a_ticket() -> None:
    with pytest.raises(RuntimeError, match="MP_TICKET is empty"):
        _client(FakeSession(), ticket="   ")


def test_get_by_date_sends_ticket_and_api_date_format() -> None:
    session = FakeSession(FakeResponse(text='{"Cantidad": 1, "Listado": [{"CodigoExterno": "1-1-LE26"}]}'))

    payload = _client(session).get_licitaciones_by_date("2026-04-04", estado="publicada")

    assert payload["Cantidad"] == 1
    call = session.calls[0]
    assert call["method"] == "GET"
    assert call["url"] == "https://api.example.test/licitaciones.json"
    assert call["params"] == {"ticket": "ticket-de-prueba", "fecha": "04042026", "estado": "publicada"}
    assert call["timeout"] == 7


def test_get_by_code_sends_the_code() -> None:
    session = FakeSession(FakeResponse())

    _client(session).get_licitacion_by_code("1292-6-LE26")

    assert session.calls[0]["params"] == {"ticket": "ticket-de-prueba", "codigo": "1292-6-LE26"}


def test_request_is_retried_after_a_server_error() -> None:
    session = FakeSession(FakeResponse(status_code=500, text="error"), FakeResponse())

    payload = _client(session).get_licitaciones_today()

    assert payload == {"Cantidad": 0, "Listado": []}
    assert len(session.calls) == 2


def test_request_is_retried_after_a_connection_error() -> None:
    session = FakeSession(requests.ConnectionError("sin red"), FakeResponse())

    _client(session).get_licitaciones_today()

    assert len(session.calls) == 2


@pytest.mark.parametrize(
    "bad_response",
    [
        FakeResponse(status_code=503, text="no disponible"),
        FakeResponse(text="   "),
        FakeResponse(text="<html>no es json</html>"),
        FakeResponse(text="[1, 2, 3]"),
    ],
    ids=["http-error", "cuerpo-vacio", "json-invalido", "json-no-es-objeto"],
)
def test_request_fails_after_exhausting_retries(bad_response: FakeResponse) -> None:
    session = FakeSession(bad_response, bad_response)

    with pytest.raises(MercadoPublicoRequestError, match="after 2 attempts"):
        _client(session, max_retries=2).get_licitaciones_today()

    assert len(session.calls) == 2
