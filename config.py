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
BACKFILL_LOOKBACK_DAYS = _int("RADAR_BACKFILL_LOOKBACK_DAYS", 30)

# --- Email (Fase E) ---
MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
MAIL_TO = os.environ.get("MAIL_TO", "felixpineu@gmail.com")
MAIL_FROM = os.environ.get("MAIL_FROM", MAIL_USERNAME)

# --- IA (Fase D, opcional — degradação graciosa se não houver chave) ---
AI_API_KEY = os.environ.get("AI_API_KEY", "")
AI_PROVIDER = os.environ.get("AI_PROVIDER", "anthropic")
AI_THRESHOLD = _int("RADAR_AI_THRESHOLD", 40)

# --- Scoring (Fase C; pesos fora do código) ---
SCORING_CONFIG = str(BASE_DIR / "config" / "scoring.yaml")
