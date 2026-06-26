# -*- coding: utf-8 -*-
"""
filters.py — Perfil de interesse da Fórum Estudante (v2, apertado).
Partilhado por TODAS as fontes (TED, BASE, DR), para o critério ser uniforme.

Mudanças v2 (após feedback real):
- Comparação por PALAVRA INTEIRA (corrige o bug "formação" dentro de "informação").
- CPV "forte" = qualifica sozinho (áreas core); software/TI genérico deixou de ser core.
- Exclusões reforçadas (médico/radiologia, veículos, máquinas, infraestrutura/TI, etc.).
- Regra de inclusão: só entra se houver CPV forte OU pelo menos 2 palavras-chave
  (um único termo fraco já não chega — corta o ruído médico/veículos/etc.).
"""

import re

# CPV que qualificam SOZINHOS (áreas core da Fórum Estudante).
CPV_FORTE = [
    # Comunicação, publicidade, marketing, RP, design, fotografia
    "79340", "79341", "79342", "79413", "79416", "79822", "79961", "79970",
    # Eventos, congressos, seminários, feiras
    "79950", "79951", "79952", "79953", "79954", "79956",
    # Produção audiovisual, vídeo, conteúdos, cultura
    "92111", "92112", "92211", "92400",
    # Educação e formação
    "80400", "80500", "80510", "80520", "80521", "80522", "80530",
    # Web/digital específico (design de sites, desenvolvimento internet)
    "72413", "72420",
]

# Palavras-chave de interesse (comparação por palavra inteira).
TERMOS_INTERESSE = [
    "comunicação", "campanha", "marketing", "evento", "eventos", "congresso",
    "conferência", "seminário", "workshop", "bootcamp", "academia", "formação",
    "ensino", "educação", "vídeo", "audiovisual", "fotografia", "design",
    "branding", "redes sociais", "website", "websites", "conteúdos", "produção",
    "publicitário", "publicidade", "assessoria", "relações públicas", "literacia",
    "juventude", "empregabilidade", "plataforma digital", "desenvolvimento web",
]

# Exclusões fortes (se aparecerem no título, descarta logo).
TERMOS_EXCLUIR = [
    "obras", "construção", "empreitada", "engenharia", "arquitetura", "limpeza",
    "vigilância", "segurança", "alimentação", "catering", "refeições",
    "hospitalar", "hospital", "clínic", "médic", "radiolog", "imagiolog",
    "cirurg", "enfermag", "arco em c", "pacs", "veículo", "automóvel", "viatura",
    "combustível", "mobiliário", "agrícola", "florestal", "resíduo", "saneamento",
    "abastecimento de água", "seguro", "máquina", "manutenção", "reparação",
    "infraestrutura", "vmware", "servidor",
]


def _tem_palavra(termo, texto_lower):
    """True se 'termo' aparece como palavra inteira em texto_lower."""
    return re.search(r"\b" + re.escape(termo) + r"\b", texto_lower) is not None


def interessa(op):
    """op normalizada: precisa de 'titulo' (str) e 'cpvs' (lista de str).
    Devolve (incluir: bool, score: int, motivos: list[str])."""
    titulo = (op.get("titulo") or "")
    tl = titulo.lower()

    for e in TERMOS_EXCLUIR:
        if e in tl:
            return (False, 0, [])

    cpvs = op.get("cpvs") or []
    forte = any(any(str(c).startswith(p) for p in CPV_FORTE) for c in cpvs)
    termos = sorted({t for t in TERMOS_INTERESSE if _tem_palavra(t, tl)})

    # Regra de inclusão: CPV forte OU >= 2 palavras-chave.
    if not (forte or len(termos) >= 2):
        return (False, 0, [])

    score = (2 if forte else 0) + len(termos)
    motivos = []
    if forte:
        motivos.append("CPV na área de interesse")
    if termos:
        motivos.append("Palavras-chave: " + ", ".join(termos[:5]))
    return (True, score, motivos)


def estrelas(score):
    if score >= 4:
        return "⭐⭐⭐ Concorrer"
    if score >= 2:
        return "⭐⭐ Analisar"
    return "⭐ Apenas acompanhar"
