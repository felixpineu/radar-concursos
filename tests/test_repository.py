# -*- coding: utf-8 -*-
"""Testa a deduplicação/ingestão do repository com SQLite em memória."""

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from database.models import Base, Tender, TenderSource, TenderCpv, Entity
from database import repository


@pytest.fixture()
def sessao():
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    s = Session()
    yield s
    s.close()


def _rec(**kw):
    base = {
        "source": "ted", "source_url": "https://x/1", "source_procedure_number": "100/2026",
        "entity_name": "Câmara Municipal de X (500000001)", "entity_nif": "500000001",
        "title": "Aquisição de serviços de comunicação", "description": "",
        "base_value": 20000.0, "currency": "EUR", "publication_date": "2026-06-20",
        "deadline": "2026-07-10", "cpvs": ["79341000-6"], "procedure_type": "concurso público",
        "location": None, "raw_payload": {"k": "v"},
    }
    base.update(kw)
    return base


def test_ingest_cria_novo(sessao):
    tender, is_new = repository.ingest(sessao, _rec())
    assert is_new is True
    assert tender.id is not None
    assert tender.base_value == 20000.0
    assert len(tender.sources) == 1
    assert {c.cpv for c in tender.cpvs} == {"79341000-6"}
    assert sessao.scalars(select(Entity)).first().nif == "500000001"


def test_reingest_identico_idempotente(sessao):
    repository.ingest(sessao, _rec())
    tender, is_new = repository.ingest(sessao, _rec())
    assert is_new is False
    assert len(sessao.scalars(select(Tender)).all()) == 1
    assert len(sessao.scalars(select(TenderSource)).all()) == 1  # mesma (source,url)


def test_mesma_fonte_url_diferente_acrescenta_deteccao(sessao):
    repository.ingest(sessao, _rec())
    # mesmo procedure_number, URL diferente -> mesmo canónico, 2 deteções
    tender, is_new = repository.ingest(sessao, _rec(source_url="https://x/2"))
    assert is_new is False
    assert len(sessao.scalars(select(Tender)).all()) == 1
    assert len(tender.sources) == 2


def test_dedup_cruzada_ted_e_base(sessao):
    # TED e BASE veem o mesmo concurso: procedure_number diferente, mas dedup_hash igual
    repository.ingest(sessao, _rec(source="ted", source_url="https://ted/1",
                                   source_procedure_number="TED-1"))
    tender, is_new = repository.ingest(sessao, _rec(
        source="base", source_url="https://base/1", source_procedure_number=None))
    # casam pelo dedup_hash (mesma entidade+título+valor+prazo)
    assert is_new is False
    assert len(sessao.scalars(select(Tender)).all()) == 1
    assert {ts.source for ts in tender.sources} == {"ted", "base"}


def test_cpvs_nao_duplicam(sessao):
    repository.ingest(sessao, _rec(cpvs=["79341000-6", "79952000-2"]))
    repository.ingest(sessao, _rec(source_url="https://x/2", cpvs=["79341000-6", "92111000-2"]))
    cpvs = {c.cpv for c in sessao.scalars(select(TenderCpv)).all()}
    assert cpvs == {"79341000-6", "79952000-2", "92111000-2"}


def test_get_unemailed_e_mark_emailed(sessao):
    t, _ = repository.ingest(sessao, _rec())
    assert len(repository.get_unemailed(sessao)) == 1
    repository.mark_emailed(sessao, [t.id])
    assert repository.get_unemailed(sessao) == []
