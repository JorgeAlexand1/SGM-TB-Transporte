# -*- coding: utf-8 -*-
"""Permite ejecutar los tests de lib/ con pytest sin Odoo: `pytest addons/transporte_gps_traccar/tests/pytest`."""
import os
import sys

LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))
if LIB not in sys.path:
    sys.path.insert(0, LIB)
