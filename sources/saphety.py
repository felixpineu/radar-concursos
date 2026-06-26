# -*- coding: utf-8 -*-
"""sources/saphety.py — stub de interface. NÃO implementar nesta fase."""

from sources.base_source import BaseSource


class SaphetySource(BaseSource):
    name = "saphety"
    active = False

    def fetch(self, mode, since):
        return ([], "Fonte Saphety não implementada (planeada).")
