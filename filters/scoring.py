# -*- coding: utf-8 -*-
"""
filters/scoring.py — motor de pontuação.

Lê os pesos de config/scoring.yaml (fora do código). Para cada concurso calcula
score, classification e score_signals (exatamente que critérios contribuíram).
Regras: CPV pesa mais que palavra-chave; palavras por palavra inteira; negativos
penalizam; hard_exclude exclui à força (classification='ignorar').
"""

import yaml

import config
from filters import cpv as cpv_mod
from filters import keywords as kw_mod
from filters import negative as neg_mod

CLASSIF_ESTRELAS = {
    "concorrer": "⭐⭐⭐ Concorrer",
    "analisar": "⭐⭐ Analisar",
    "acompanhar": "⭐ Acompanhar",
    "ignorar": "—",
}

_CACHE = {}


def carregar_pesos(caminho=None):
    caminho = caminho or config.SCORING_CONFIG
    if caminho not in _CACHE:
        with open(caminho, encoding="utf-8") as f:
            _CACHE[caminho] = yaml.safe_load(f)
    return _CACHE[caminho]


def _classificar(score, limiares):
    if score >= limiares.get("concorrer", 60):
        return "concorrer"
    if score >= limiares.get("analisar", 40):
        return "analisar"
    if score >= limiares.get("acompanhar", 20):
        return "acompanhar"
    return "ignorar"


def pontuar(title, description, cpvs, pesos=None):
    """Devolve (score:int, classification:str, signals:dict)."""
    pesos = pesos or carregar_pesos()
    pos = pesos.get("positivos") or {}
    texto_lower = f"{title or ''} {description or ''}".lower()

    hard = neg_mod.hard_excluido(texto_lower, pesos.get("hard_exclude"))
    if hard:
        return (0, "ignorar", {"hard_exclude": [hard]})

    cpv_hits = cpv_mod.match_cpvs(cpvs, pos.get("cpv") or {})
    kw_hits = kw_mod.match_keywords(texto_lower, pos.get("keywords") or {})
    neg_hits = neg_mod.match_negativos(texto_lower, pesos.get("negativos") or {})

    score = (sum(p for _, _, p in cpv_hits)
             + sum(p for _, p in kw_hits)
             + sum(p for _, p in neg_hits))

    classification = _classificar(score, pesos.get("limiares") or {})
    signals = {
        "cpv": [{"cpv": c, "prefixo": pre, "peso": p} for c, pre, p in cpv_hits],
        "keywords": [{"termo": t, "peso": p} for t, p in kw_hits],
        "negativos": [{"termo": t, "peso": p} for t, p in neg_hits],
    }
    return (int(score), classification, signals)


def pontuar_tender(tender, pesos=None):
    """Pontua um objeto Tender e grava score/classification/score_signals."""
    score, classification, signals = pontuar(
        tender.title, tender.description, [c.cpv for c in tender.cpvs], pesos)
    tender.score = score
    tender.classification = classification
    tender.score_signals = signals
    return tender
