"""ORM tables for persistence."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LicitationRecord(Base):
    """Persistence table for normalized licitation records."""

    __tablename__ = "licitations"
    __table_args__ = (
        UniqueConstraint("codigo_externo", "fecha_extraccion", name="uq_licitacion_extraccion"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo_externo: Mapped[str | None] = mapped_column(String(64), index=True)
    nombre: Mapped[str | None] = mapped_column(String(500))
    estado_nombre: Mapped[str | None] = mapped_column(String(120), index=True)
    organismo_nombre: Mapped[str | None] = mapped_column(String(255), index=True)
    region: Mapped[str | None] = mapped_column(String(120), index=True)
    monto_estimado: Mapped[float | None] = mapped_column(Float)
    moneda: Mapped[str | None] = mapped_column(String(32))
    url_licitacion: Mapped[str | None] = mapped_column(String(500))
    score_oportunidad: Mapped[float | None] = mapped_column(Float, index=True)
    fecha_extraccion: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
