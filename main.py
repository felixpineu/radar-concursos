#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py — Ponto de entrada do Radar de Concursos.

Uso: python main.py --mode {backfill|daily}
  - daily:    janela curta (últimos N dias); ingestão -> dedup -> [scoring] -> [IA] -> [email].
  - backfill: janela larga; popula a BD; não envia email.

Nesta fase (A+B) faz: recolha das fontes ativas (resiliente) -> ingestão/dedup na BD
-> registo da execução em `runs`. Scoring (Fase C), IA (Fase D) e email (Fase E)
entram a seguir, nos pontos marcados com TODO.
"""

import sys
import argparse
import datetime as dt

import config
from database import database, repository
from sources.ted import TedSource
from sources.base import BaseGovSource
from sources.dr import DrSource
from sources.vortal import VortalSource
from sources.acingov import AcinGovSource
from sources.saphety import SaphetySource

# Ordem de execução das fontes (inativas são saltadas).
FONTES = [
    TedSource(), BaseGovSource(), DrSource(),
    VortalSource(), AcinGovSource(), SaphetySource(),
]


def _since(mode):
    dias = (config.BACKFILL_LOOKBACK_DAYS if mode == "backfill"
            else config.DAILY_LOOKBACK_DAYS)
    return dt.date.today() - dt.timedelta(days=dias)


def correr(mode):
    database.init_db()
    since = _since(mode)
    sources_report = {}
    total_proc = 0
    total_novos = 0

    with database.session_scope() as sessao:
        run = repository.start_run(sessao, mode)

        for fonte in FONTES:
            if not getattr(fonte, "active", False):
                sources_report[fonte.name] = {"ativa": False}
                continue

            try:
                registos, estado = fonte.fetch(mode, since)
            except Exception as e:  # uma fonte falhar NÃO derruba as outras
                sources_report[fonte.name] = {
                    "ativa": True, "erro": f"{type(e).__name__}: {e}"}
                print(f"[{fonte.name}] ERRO: {e}", file=sys.stderr)
                continue

            novos_fonte = 0
            ingeridos = 0
            for rec in registos:
                try:
                    _tender, is_new = repository.ingest(sessao, rec)
                    ingeridos += 1
                    total_proc += 1
                    if is_new:
                        novos_fonte += 1
                        total_novos += 1
                except Exception as e:  # um registo mau não mata a fonte
                    print(f"[{fonte.name}] registo ignorado: {e}", file=sys.stderr)

            sources_report[fonte.name] = {
                "ativa": True, "estado": estado,
                "recolhidos": len(registos), "ingeridos": ingeridos,
                "novos": novos_fonte,
            }
            print(f"[{fonte.name}] {estado} | novos: {novos_fonte}")

        # --- Fase C: scoring (re-pontua tudo; pesos podem ter mudado) ---
        from filters import scoring
        pesos = scoring.carregar_pesos()
        for tender in repository.get_tenders_for_scoring(sessao):
            scoring.pontuar_tender(tender, pesos)
        sessao.flush()

        # --- Fase D: IA nos candidatos acima do limiar (degradação graciosa) ---
        ai_processados = 0
        if config.AI_API_KEY:
            from datetime import datetime
            from ai import summarize
            for tender in repository.get_tenders_for_scoring(sessao):
                if tender.ai_processed_at is not None:
                    continue
                if (tender.score or 0) < config.AI_THRESHOLD:
                    continue
                enriquecido = summarize.enrich(tender)
                if enriquecido:
                    for campo, valor in enriquecido.items():
                        setattr(tender, campo, valor)
                    tender.ai_processed_at = datetime.utcnow()
                    ai_processados += 1
            sessao.flush()
            if ai_processados:
                print(f"[ia] {ai_processados} concursos enriquecidos.")

        # TODO Fase E: email dos novos (repository.get_unemailed -> emailing.mail)

        houve_erro = any("erro" in v for v in sources_report.values())
        status = "partial" if houve_erro else "success"
        repository.finish_run(
            sessao, run, status, sources_report,
            total_novos, total_proc, emailed_count=0,
            notes=f"modo={mode}; since={since.isoformat()}")

    print(f"\nOK ({mode}) — {total_novos} novos / {total_proc} processados. "
          f"Estado: {status}.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Radar de Concursos — Fórum Estudante")
    parser.add_argument("--mode", choices=["backfill", "daily"], default="daily")
    args = parser.parse_args(argv)
    return correr(args.mode)


if __name__ == "__main__":
    sys.exit(main())
