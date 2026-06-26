# -*- coding: utf-8 -*-
"""
ai/summarize.py — enriquecimento por IA (opcional, degradação graciosa).

Para um concurso acima do limiar de scoring, produz, numa única chamada à API da
Anthropic (SDK oficial), com saída estruturada:
  - resumo do objeto
  - porque interessa à Fórum Estudante
  - oportunidades
  - riscos
  - sugestão de classificação (complementa o score, não o substitui)

Degradação graciosa: sem chave (config.AI_API_KEY) ou em qualquer erro, devolve None
e o sistema segue só com o scoring. Nunca derruba a execução.
"""

import config
from ai import classify

# Schema de saída estruturada (output_config.format).
_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "why": {"type": "string"},
        "opportunities": {"type": "string"},
        "risks": {"type": "string"},
        "suggested_classification": {
            "type": "string",
            "enum": ["concorrer", "analisar", "acompanhar", "ignorar"],
        },
    },
    "required": ["summary", "why", "opportunities", "risks", "suggested_classification"],
    "additionalProperties": False,
}

_SISTEMA = (
    "És um analista de contratação pública da Fórum Estudante, uma empresa de media e "
    "comunicação para jovens (eventos, campanhas, conteúdos, vídeo/audiovisual, "
    "formação, educação, design, websites/plataformas digitais, literacia, "
    "empregabilidade). Avalias concursos públicos do ponto de vista do interesse "
    "comercial da Fórum Estudante. Responde sempre em português de Portugal, conciso."
)


def _prompt(tender):
    cpvs = ", ".join(c.cpv for c in tender.cpvs) or "—"
    return (
        f"Concurso público:\n"
        f"- Objeto: {tender.title}\n"
        f"- Descrição: {tender.description or '—'}\n"
        f"- Entidade: {tender.entity.nome if tender.entity else '—'}\n"
        f"- Preço base: {tender.base_value} {tender.currency}\n"
        f"- Tipo de procedimento: {tender.procedure_type or '—'}\n"
        f"- CPVs: {cpvs}\n"
        f"- Score interno: {tender.score} ({tender.classification})\n\n"
        f"Produz: resumo do objeto; porque interessa (ou não) à Fórum Estudante; "
        f"oportunidades; riscos; e uma classificação sugerida "
        f"(concorrer/analisar/acompanhar/ignorar)."
    )


def enrich(tender):
    """Devolve dict com ai_summary/ai_why/ai_opportunities/ai_risks/
    ai_suggested_classification, ou None se a IA não estiver disponível/falhar."""
    if not config.AI_API_KEY:
        return None
    try:
        import anthropic
    except Exception:
        return None

    try:
        client = anthropic.Anthropic(api_key=config.AI_API_KEY)
        resp = client.messages.create(
            model=config.AI_MODEL,
            max_tokens=1500,
            system=_SISTEMA,
            messages=[{"role": "user", "content": _prompt(tender)}],
            output_config={"format": {"type": "json_schema", "schema": _SCHEMA},
                           "effort": "low"},
        )
        import json
        texto = next((b.text for b in resp.content if b.type == "text"), "")
        dados = json.loads(texto)
    except Exception:
        return None

    return {
        "ai_summary": dados.get("summary"),
        "ai_why": dados.get("why"),
        "ai_opportunities": dados.get("opportunities"),
        "ai_risks": dados.get("risks"),
        "ai_suggested_classification":
            classify.normalizar_classificacao(dados.get("suggested_classification")),
    }
