# -*- coding: utf-8 -*-
"""Testa o render do briefing e o gate de envio (sem SMTP real)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import config
from database.models import Base
from database import repository
from emailing import mail


@pytest.fixture()
def sessao():
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine, expire_on_commit=False, future=True)()
    yield s
    s.close()


def _rec(**kw):
    base = {
        "source": "base", "source_url": "https://base/1", "source_procedure_number": "1/2026",
        "entity_name": "Câmara X (500000001)", "title": "Serviços de comunicação e eventos",
        "description": "", "base_value": 15000.0, "currency": "EUR",
        "publication_date": "2026-06-20", "deadline": "2026-07-10",
        "cpvs": ["79341000-6"], "procedure_type": "Concurso público", "raw_payload": {},
    }
    base.update(kw)
    return base


def test_render_contem_concurso_e_limitacoes(sessao):
    t, _ = repository.ingest(sessao, _rec())
    t.score = 70
    t.classification = "concorrer"
    html = mail.render([t])
    assert "Serviços de comunicação e eventos" in html
    assert "Concorrer" in html
    assert "Limitações de cobertura" in html


def test_render_vazio(sessao):
    html = mail.render([])
    assert "Sem concursos novos" in html


def test_enviar_briefing_backfill_nao_envia(sessao):
    assert mail.enviar_briefing(sessao, "backfill") == (0, "Modo backfill — email não enviado.")


def test_enviar_briefing_sem_credenciais(sessao, monkeypatch):
    monkeypatch.setattr(config, "MAIL_USERNAME", "")
    monkeypatch.setattr(config, "MAIL_PASSWORD", "")
    n, estado = mail.enviar_briefing(sessao, "daily")
    assert n == 0
    assert "sem MAIL_USERNAME" in estado
