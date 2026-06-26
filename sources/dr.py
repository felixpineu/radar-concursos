# -*- coding: utf-8 -*-
"""
sources/dr.py — Diário da República (stub).
Os anúncios do DR já são cobertos pela fonte BASE ("Anúncios DR"). Mantém-se a
interface para extensão futura sem mexer no resto.
"""

from sources.base_source import BaseSource


class DrSource(BaseSource):
    name = "dr"
    active = False

    def fetch(self, mode, since):
        return ([], "Fonte DR inativa (coberta pela fonte BASE).")
