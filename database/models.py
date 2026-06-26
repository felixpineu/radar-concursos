# -*- coding: utf-8 -*-
"""
database/models.py — Modelo de dados (SQLAlchemy 2.0).

Tipos portáteis (String, Text, Numeric, Date, DateTime, JSON) para que a migração
SQLite -> PostgreSQL/Supabase seja transparente. Todo o ACESSO à BD passa por
database/repository.py — nunca SQL espalhado pelo resto do código.
"""

import datetime as dt
from typing import Optional

from sqlalchemy import (
    String, Integer, Text, Numeric, Date, DateTime, JSON,
    ForeignKey, UniqueConstraint, func,
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship,
)


class Base(DeclarativeBase):
    pass


class Entity(Base):
    """Entidade adjudicante normalizada."""
    __tablename__ = "entities"

    id: Mapped[int] = mapped_column(primary_key=True)
    # nif é único quando presente — unicidade garantida no repository (partial
    # unique não é portátil entre SQLite/Postgres). Indexado para lookups rápidos.
    nif: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    nome: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now())

    tenders: Mapped[list["Tender"]] = relationship(back_populates="entity")


class Tender(Base):
    """Concurso canónico — um por procedimento, mesmo que visto em várias fontes."""
    __tablename__ = "tenders"

    id: Mapped[int] = mapped_column(primary_key=True)
    procedure_number: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    entity_id: Mapped[Optional[int]] = mapped_column(ForeignKey("entities.id"))

    title: Mapped[str] = mapped_column(String(1000))
    description: Mapped[Optional[str]] = mapped_column(Text)
    base_value: Mapped[Optional[float]] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(10), default="EUR")
    publication_date: Mapped[Optional[dt.date]] = mapped_column(Date)
    deadline: Mapped[Optional[dt.date]] = mapped_column(Date)
    procedure_type: Mapped[Optional[str]] = mapped_column(String(200))
    location: Mapped[Optional[str]] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(30), default="unknown")

    # Scoring (Fase C)
    score: Mapped[int] = mapped_column(Integer, default=0)
    classification: Mapped[Optional[str]] = mapped_column(String(50))
    score_signals: Mapped[Optional[dict]] = mapped_column(JSON)

    # IA (Fase D)
    ai_summary: Mapped[Optional[str]] = mapped_column(Text)
    ai_why: Mapped[Optional[str]] = mapped_column(Text)
    ai_opportunities: Mapped[Optional[str]] = mapped_column(Text)
    ai_risks: Mapped[Optional[str]] = mapped_column(Text)
    ai_suggested_classification: Mapped[Optional[str]] = mapped_column(String(50))
    ai_processed_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime)

    # Deduplicação e ciclo de vida
    dedup_hash: Mapped[str] = mapped_column(String(64), index=True)
    first_detected_at: Mapped[dt.datetime] = mapped_column(DateTime, default=func.now())
    last_processed_at: Mapped[dt.datetime] = mapped_column(DateTime, default=func.now())
    emailed_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now())

    entity: Mapped[Optional["Entity"]] = relationship(back_populates="tenders")
    sources: Mapped[list["TenderSource"]] = relationship(
        back_populates="tender", cascade="all, delete-orphan")
    cpvs: Mapped[list["TenderCpv"]] = relationship(
        back_populates="tender", cascade="all, delete-orphan")


class TenderSource(Base):
    """Cada deteção de um concurso numa fonte (TED, BASE, ...)."""
    __tablename__ = "tender_sources"
    __table_args__ = (
        UniqueConstraint("source", "source_url", name="uq_source_source_url"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tender_id: Mapped[int] = mapped_column(ForeignKey("tenders.id"))
    source: Mapped[str] = mapped_column(String(30))
    source_url: Mapped[str] = mapped_column(String(600))
    source_procedure_number: Mapped[Optional[str]] = mapped_column(String(100))
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSON)
    detected_at: Mapped[dt.datetime] = mapped_column(DateTime, default=func.now())

    tender: Mapped["Tender"] = relationship(back_populates="sources")


class TenderCpv(Base):
    """CPV por concurso (join, para estatísticas 'por CPV')."""
    __tablename__ = "tender_cpvs"

    tender_id: Mapped[int] = mapped_column(ForeignKey("tenders.id"), primary_key=True)
    cpv: Mapped[str] = mapped_column(String(20), primary_key=True)

    tender: Mapped["Tender"] = relationship(back_populates="cpvs")


class Run(Base):
    """Histórico de execuções (observabilidade)."""
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    mode: Mapped[str] = mapped_column(String(20))
    started_at: Mapped[dt.datetime] = mapped_column(DateTime, default=func.now())
    finished_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="running")
    sources_json: Mapped[Optional[dict]] = mapped_column(JSON)
    new_tenders: Mapped[int] = mapped_column(Integer, default=0)
    total_processed: Mapped[int] = mapped_column(Integer, default=0)
    emailed_count: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text)
