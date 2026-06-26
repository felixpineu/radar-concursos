# -*- coding: utf-8 -*-
"""filters/keywords.py — correspondência de palavras-chave por PALAVRA INTEIRA.

Correção transportada do filtro v2: comparar por palavra inteira evita que
'formação' case dentro de 'informação'. Acentos preservados (o texto é comparado
em minúsculas mas com acentos, tal como as chaves do scoring.yaml)."""

import re


def _tem_palavra(termo, texto_lower):
    # \b em volta; termos com espaços (ex.: 'ensino superior') também funcionam.
    return re.search(r"(?<!\w)" + re.escape(termo) + r"(?!\w)", texto_lower) is not None


def match_keywords(texto_lower, pesos_keywords):
    """Devolve lista de (termo, peso) para as palavras-chave presentes."""
    hits = []
    for termo, peso in pesos_keywords.items():
        if _tem_palavra(str(termo).lower(), texto_lower):
            hits.append((str(termo), peso))
    return hits
