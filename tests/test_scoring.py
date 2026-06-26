# -*- coding: utf-8 -*-
"""Testa o motor de scoring com entradas conhecidas -> score/classificação esperados."""

from filters import scoring


def test_cpv_forte_classifica_concorrer():
    score, classif, sig = scoring.pontuar(
        "Aquisição de serviços de comunicação e marketing", "",
        ["79341000-6"])
    # CPV 79341 (30) + keywords 'comunicação'(20)+'marketing'(20) = 70 -> concorrer
    assert score == 70
    assert classif == "concorrer"
    assert sig["cpv"][0]["prefixo"] == "79341"
    assert {k["termo"] for k in sig["keywords"]} == {"comunicação", "marketing"}


def test_palavra_inteira_nao_casa_dentro_de_outra():
    # 'formação' NÃO deve casar dentro de 'informação'
    score, classif, sig = scoring.pontuar(
        "Sistema de informação de gestão", "", [])
    assert all(k["termo"] != "formação" for k in sig["keywords"])


def test_hard_exclude_forca_ignorar():
    score, classif, sig = scoring.pontuar(
        "Empreitada de obras de construção do edifício", "",
        ["79341000-6"])  # mesmo com CPV forte
    assert classif == "ignorar"
    assert "obras" in sig.get("hard_exclude", []) or "empreitada" in sig.get("hard_exclude", [])


def test_negativos_penalizam():
    score, classif, sig = scoring.pontuar(
        "Aquisição de mobiliário e equipamento de vídeo", "", [])
    # 'vídeo'(+15) + 'mobiliário'(-40) = -25 -> ignorar
    assert score == -25
    assert classif == "ignorar"


def test_limiar_acompanhar():
    score, classif, sig = scoring.pontuar(
        "Serviços de fotografia", "", [])  # fotografia = 10... abaixo de 20
    assert classif == "ignorar"
    score2, classif2, _ = scoring.pontuar(
        "Serviços de fotografia e website", "", [])  # 10 + 10 = 20 -> acompanhar
    assert score2 == 20
    assert classif2 == "acompanhar"
