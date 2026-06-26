# -*- coding: utf-8 -*-
"""
database/database.py — engine, sessão e inicialização.

Centraliza a ligação à BD (lê config.DB_URL). Mudar de SQLite para
PostgreSQL/Supabase = mudar apenas RADAR_DB_URL em config.py.
"""

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import config
from database.models import Base

engine = create_engine(config.DB_URL, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)


def init_db():
    """Cria as tabelas que ainda não existem."""
    Base.metadata.create_all(engine)


@contextmanager
def session_scope():
    """Sessão transacional: commit no fim, rollback em erro, fecha sempre."""
    sessao = SessionLocal()
    try:
        yield sessao
        sessao.commit()
    except Exception:
        sessao.rollback()
        raise
    finally:
        sessao.close()
