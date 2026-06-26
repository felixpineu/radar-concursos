# -*- coding: utf-8 -*-
"""
sources/base_source.py — contrato comum a todas as fontes.

Cada fonte implementa fetch(mode, since) -> (lista_de_registos_normalizados, estado).
NÃO filtra nem pontua — só recolhe e normaliza. Falhas são apanhadas pela própria
fonte (try/except) e reportadas no 'estado', sem interromper as outras fontes.

Registo normalizado (igual para todas as fontes):
{
  "source": str,                      # "ted" | "base" | ...
  "source_url": str,                  # link da ficha
  "source_procedure_number": str,
  "entity_name": str,
  "entity_nif": str | None,
  "title": str,                       # objeto
  "description": str,
  "base_value": float | None,
  "currency": "EUR",
  "publication_date": "YYYY-MM-DD",
  "deadline": "YYYY-MM-DD" | None,
  "cpvs": [str],
  "procedure_type": str,              # concurso público | concurso limitado | ...
  "location": str | None,
  "raw_payload": dict                 # original, para reprocessamento futuro
}
"""


class BaseSource:
    name = "base_source"
    active = False

    def fetch(self, mode, since):
        """mode: 'backfill'|'daily'; since: datetime.date (limite inferior).
        Devolve (lista[dict_normalizado], estado:str)."""
        raise NotImplementedError
