# -*- coding: utf-8 -*-
"""
ai/classify.py — reconciliação da classificação sugerida pela IA.

A IA complementa o scoring, não o substitui. Aqui apenas validamos/normalizamos
a classificação que a IA sugere para um valor canónico do sistema.
"""

CLASSIF_VALIDAS = {"concorrer", "analisar", "acompanhar", "ignorar"}

_SINONIMOS = {
    "concorrer": "concorrer", "candidatar": "concorrer", "candidatar-se": "concorrer",
    "analisar": "analisar", "avaliar": "analisar", "analisar melhor": "analisar",
    "acompanhar": "acompanhar", "monitorizar": "acompanhar", "seguir": "acompanhar",
    "ignorar": "ignorar", "descartar": "ignorar", "rejeitar": "ignorar",
}


def normalizar_classificacao(valor):
    """Devolve uma das CLASSIF_VALIDAS, ou None se não reconhecer."""
    v = (valor or "").strip().lower()
    if v in CLASSIF_VALIDAS:
        return v
    return _SINONIMOS.get(v)
