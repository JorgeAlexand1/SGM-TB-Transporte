# -*- coding: utf-8 -*-
"""Ejecuta los tests de lib/ sin Odoo: `pytest addons/transporte_calidad/tests/pytest`."""
import os
import sys

AQUI = os.path.dirname(__file__)
for ruta in (os.path.join(AQUI, '..', '..', 'lib'),
             os.path.join(AQUI, '..', '..', '..', 'transporte_gps_traccar', 'lib')):
    ruta = os.path.abspath(ruta)
    if ruta not in sys.path:
        sys.path.insert(0, ruta)
