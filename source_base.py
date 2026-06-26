# -*- coding: utf-8 -*-
"""
source_base.py — Fonte 2 (FASE 2, ainda não ativa): Portal BASE.
Concursos públicos NACIONAIS, incluindo abaixo dos limiares europeus — exatamente
os concursos pequenos (muitas vezes < 20.000 €) em comunicação, eventos, formação,
educação, design, conteúdos, websites, audiovisual e consultoria.

Estado: por ativar. O endpoint público do BASE (/Base4/pt/resultados/) responde
vazio fora do navegador (depende de estado de sessão/JavaScript). O acesso
programático fiável é a API oficial do IMPIC, que exige registo + autorização.
Quando a autorização estiver obtida, implementa-se aqui o fetch() real.
"""

NOME = "BASE — Concursos nacionais (inclui abaixo dos limiares)"
ATIVA = False

ESTADO = ("Fonte ainda NÃO ativa — planeada para a Fase 2. "
          "Requer autorização da API do Portal BASE (IMPIC). "
          "Cobrirá concursos nacionais, incluindo os pequenos abaixo dos limiares europeus.")


def fetch():
    """Devolve (oportunidades, estado). Enquanto inativa, devolve lista vazia."""
    return ([], ESTADO)
