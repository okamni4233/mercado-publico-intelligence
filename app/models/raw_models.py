"""Raw API response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RawAPIResponse(BaseModel):
    """Flexible representation of a raw response from Mercado Publico."""

    cantidad: int | None = Field(default=None, alias="Cantidad")
    fecha_creacion: str | None = Field(default=None, alias="FechaCreacion")
    version: str | None = Field(default=None, alias="Version")
    listado: list[dict[str, Any]] = Field(default_factory=list, alias="Listado")
