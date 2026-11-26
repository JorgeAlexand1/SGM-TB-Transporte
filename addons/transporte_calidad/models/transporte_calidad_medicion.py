# -*- coding: utf-8 -*-
from odoo import api, fields, models

from odoo.addons.transporte_gps_traccar.models.gps_posicion import verificar_gestor


class TransporteCalidadMedicion(models.Model):
    """Mediciones de calidad del software: tiempos de respuesta y exactitud de la sincronización."""
    _name = 'transporte.calidad.medicion'
    _description = 'Medición de Calidad del Software'
    _order = 'fecha desc, id desc'

    fecha = fields.Datetime(default=fields.Datetime.now, required=True, index=True)
    tipo = fields.Selection([
        ('dashboard', 'Cálculo del dashboard'),
        ('mapa', 'Consulta del mapa'),
        ('consulta_viajes', 'Consulta de recorridos'),
        ('exactitud_sync', 'Exactitud Traccar ↔ Odoo'),
        ('prueba_rendimiento', 'Prueba de rendimiento'),
    ], required=True, index=True)
    duracion_ms = fields.Integer(string='Duración (ms)', group_operator='avg')
    registros = fields.Integer(string='Registros procesados')
    valor = fields.Float(string='Resultado', digits=(10, 2), group_operator='avg',
                         help='Para exactitud: % de posiciones idénticas en Traccar y Odoo.')
    ok = fields.Boolean(string='Correcta', default=True)
    detalle = fields.Text()

    @api.model
    def registrar(self, tipo, duracion_ms=0, registros=0, valor=0.0, ok=True, detalle=False):
        """Registra una medición. Devuelve el id (invocable también por XML-RPC desde scripts).

        Solo Administrador de Operaciones o procesos internos (sudo): H-A03.
        """
        verificar_gestor(self.env)
        return self.sudo().create({'tipo': tipo, 'duracion_ms': int(duracion_ms), 'registros': int(registros),
                                   'valor': valor, 'ok': ok, 'detalle': detalle}).id
