# -*- coding: utf-8 -*-
"""
config.py — Configuração central do Radar de Concursos.

Lê de variáveis de ambiente (secrets do GitHub Actions) com defaults sensatos.
A migração SQLite -> PostgreSQL/Supabase faz-se mudando apenas RADAR_DB_URL.
"""

import os
import pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parent


def _int(nome, default):
    try:
        return int(os.environ.get(nome, default))
    except (TypeError, ValueError):
        return default


# --- Base de dados (camada SQLAlchemy; só muda a connection string) ---
DB_URL = os.environ.get("RADAR_DB_URL", f"sqlite:///{BASE_DIR / 'radar.db'}")

# --- Janelas de recolha ---
DAILY_LOOKBACK_DAYS = _int("RADAR_DAILY_LOOKBACK_DAYS", 4)
BACKFILL_LOOKBACK_DAYS = _int("RADAR_BACKFILL_LOOKBACK_DAYS", 45)

# --- Email (Fase E) ---
# `or` (não default do .get): no GitHub Actions um secret inexistente é passado
# como string VAZIA, que sobreporia o default — tratamos vazio como ausente.
MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
MAIL_TO = os.environ.get("MAIL_TO") or "felixpineu@gmail.com"
MAIL_FROM = os.environ.get("MAIL_FROM") or MAIL_USERNAME

# --- IA (Fase D, opcional — degradação graciosa se não houver chave) ---
# A chave pode vir de AI_API_KEY ou ANTHROPIC_API_KEY (o SDK usa esta última).
AI_API_KEY = os.environ.get("AI_API_KEY", "") or os.environ.get("ANTHROPIC_API_KEY", "")
AI_MODEL = os.environ.get("RADAR_AI_MODEL", "claude-opus-4-8")
AI_THRESHOLD = _int("RADAR_AI_THRESHOLD", 40)

# --- Scoring (Fase C; pesos fora do código) ---
SCORING_CONFIG = str(BASE_DIR / "config" / "scoring.yaml")
