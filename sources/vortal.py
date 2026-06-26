# -*- coding: utf-8 -*-
"""sources/vortal.py — stub de interface. NÃO implementar nesta fase."""

from sources.base_source import BaseSource


class VortalSource(BaseSource):
    name = "vortal"
    active = False

    def fetch(self, mode, since):
        return ([], "Fonte Vortal não implementada (planeada).")
