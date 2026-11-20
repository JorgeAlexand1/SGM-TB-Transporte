# -*- coding: utf-8 -*-
"""Pruebas de rendimiento (A9): tiempos de respuesta con distintas cantidades de registros.

No forman parte de la suite estándar (tardan más). Ejecutar con:
    --test-tags /transporte_calidad:TestRendimiento
Los resultados se imprimen en el log (`RENDIMIENTO ...`) y se guardan como mediciones.
"""
import logging
import time
from datetime import timedelta

from odoo import fields
from odoo.tests.common import tagged

from .test_calidad import CalidadCommon

_logger = logging.getLogger(__name__)

UMBRAL_MS = 3000  # RNF-03: consultas de recorridos, mapa y métricas en < 3 s


@tagged('post_install', '-at_install', '-standard', 'rendimiento')
class TestRendimiento(CalidadCommon):

    def _medir(self, nombre, funcion, registros):
        inicio = time.perf_counter()
        resultado = funcion()
        ms = int((time.perf_counter() - inicio) * 1000)
        _logger.info('RENDIMIENTO %-22s registros=%-6s %6d ms', nombre, registros, ms)
        self.env['transporte.calidad.medicion'].registrar('prueba_rendimiento', ms, registros=registros,
                                                          detalle=nombre)
        self.assertLess(ms, UMBRAL_MS, '%s tardó %s ms con %s registros' % (nombre, ms, registros))
        return resultado

    def test_escalamiento(self):
        Dashboard = self.env['transporte.calidad.dashboard']
        Viaje = self.env['transporte.viaje']
        Bus = self.env['fleet.vehicle']
        dias_acumulados = 0
        for dias in (1, 3, 6):  # 10, 30 y 60 recorridos acumulados (~2 000 / 6 000 / 12 000 posiciones)
            nuevo = dias - dias_acumulados
            inicio = fields.Date.today() - timedelta(days=dias + 1)
            self._wizard(fecha_inicio=inicio, dias=nuevo).action_generar()
            dias_acumulados = dias
            n_viajes = Viaje.search_count([('simulado', '=', True)])
            n_pos = self.env['transporte.gps.posicion'].search_count([('simulado', '=', True)])
            self.env.invalidate_all()
            filtros = {'fecha_desde': fields.Date.to_string(fields.Date.today() - timedelta(days=30))}
            self._medir('dashboard', lambda: Dashboard.get_dashboard_data(filtros), n_viajes)
            self._medir('consulta_recorridos', lambda: Viaje.search_read(
                [('simulado', '=', True)], ['name', 'ruta_id', 'resultado', 'retraso_llegada_min'], limit=500), n_viajes)
            viaje = Viaje.search([('simulado', '=', True)], limit=1)
            self._medir('mapa_viaje', lambda: Bus.get_datos_mapa(viaje.id), n_pos)
            self._medir('reevaluar_todos', lambda: Viaje._reevaluar_todos(), n_pos)
