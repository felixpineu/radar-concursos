# -*- coding: utf-8 -*-
"""
source_dre.py — Fonte 3 (FASE 2, ainda não ativa): Diário da República.
Leitura dos "Anúncios de procedimento" publicados no DR (fonte legal primária dos
concursos públicos nacionais).

Estado: por ativar. O diariodarepublica.pt é uma aplicação JavaScript (SPA) sem
JSON/RSS público; o INCM remete os reutilizadores de dados para a API do BASE.
A implementação real entrará quando definirmos a via de leitura (ex.: via BASE/IMPIC
ou leitura assistida por navegador).
"""

NOME = "Diário da República — Anúncios nacionais"
ATIVA = False

ESTADO = ("Fonte ainda NÃO ativa — planeada para a Fase 2. "
          "Leitura dos anúncios de procedimento do Diário da República "
          "(fonte legal primária dos concursos nacionais).")


def fetch():
    return ([], ESTADO)
