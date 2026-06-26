# -*- coding: utf-8 -*-
"""Testa a degradação graciosa da IA e a normalização da classificação."""

import config
from ai import classify, summarize


def test_normalizar_classificacao():
    assert classify.normalizar_classificacao("Concorrer") == "concorrer"
    assert classify.normalizar_classificacao("candidatar-se") == "concorrer"
    assert classify.normalizar_classificacao("monitorizar") == "acompanhar"
    assert classify.normalizar_classificacao("xpto") is None
    assert classify.normalizar_classificacao(None) is None


def test_enrich_sem_chave_devolve_none(monkeypatch):
    # Sem chave -> degradação graciosa, não tenta chamar a API.
    monkeypatch.setattr(config, "AI_API_KEY", "")

    class _Fake:
        score = 90
        classification = "concorrer"
        title = "x"
        description = ""
        base_value = 1
        currency = "EUR"
        procedure_type = "concurso público"
        entity = None
        cpvs = []

    assert summarize.enrich(_Fake()) is None
