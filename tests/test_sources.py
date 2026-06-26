# -*- coding: utf-8 -*-
"""Testa a normalização das fontes a partir de payload real (sem rede)."""

from sources import ted, base


def test_ted_normalize_notice():
    notice = {
        "publication-number": "430277-2026",
        "notice-title": {"por": "Aquisição de serviços de comunicação"},
        "buyer-name": {"por": "Município de Lisboa"},
        "classification-cpv": ["79341000-6", "79952000-2"],
        "deadline-receipt-tender-date-lot": ["2026-07-15Z"],
        "total-value": ["250000"],
        "notice-type": "cn-standard",
        "publication-date": "2026-06-24+01:00",
        "place-of-performance": {"por": "Lisboa"},
    }
    rec = ted.normalize_notice(notice)
    assert rec["source"] == "ted"
    assert rec["source_url"] == "https://ted.europa.eu/pt/notice/-/detail/430277-2026"
    assert rec["base_value"] == 250000.0
    assert rec["deadline"] == "2026-07-15"
    assert rec["publication_date"] == "2026-06-24"
    assert rec["cpvs"] == ["79341000-6", "79952000-2"]
    assert rec["location"] == "Lisboa"


def test_ted_ignora_nao_concurso():
    assert ted.normalize_notice({"notice-type": "can-standard"}) is None  # award notice


def test_base_normalize_detalhe_elegivel():
    dados = {
        "Nº do anúncio DR": "16311/2026",
        "Diário da república": "nº 121 série 2, de 25-06-2026",
        "Entidade emissora": "Águas do Douro e Paiva, SA (514310774)",
        "Descrição": "Aquisição de serviços de design e comunicação",
        "Tipo de modelo": "Concurso público",
        "Preço base": "20.000,00 €",
        "CPVs": "79822500-7, Serviços de design gráfico",
        "Prazo para apresentação de propostas": "12 dias.",
    }
    rec = base.normalize_detalhe(dados, "https://base/detalhe?id=1")
    assert rec["source"] == "base"
    assert rec["source_procedure_number"] == "16311/2026"
    assert rec["entity_nif"] == "514310774"
    assert rec["base_value"] == 20000.0
    assert rec["publication_date"] == "2026-06-25"
    assert rec["deadline"] == "2026-07-07"   # 25-06 + 12 dias
    assert rec["cpvs"] == ["79822500-7"]
    assert rec["procedure_type"] == "Concurso público"


def test_base_normalize_rejeita_modelo_nao_elegivel():
    dados = {"Nº do anúncio DR": "1/2026", "Tipo de modelo": "Ajuste direto"}
    assert base.normalize_detalhe(dados, "u") is None


def test_base_normalize_sem_numero():
    assert base.normalize_detalhe({"Tipo de modelo": "Concurso público"}, "u") is None
