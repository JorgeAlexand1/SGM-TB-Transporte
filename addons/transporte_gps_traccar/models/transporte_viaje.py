# -*- coding: utf-8 -*-
from odoo import _, api, fields, models

from ..lib import geo_utils


class TransporteViaje(models.Model):
    _inherit = 'transporte.viaje'

    posicion_ids = fields.One2many('transporte.gps.posicion', 'viaje_id', string='Posiciones GPS')
    cantidad_posiciones = fields.Integer(compute='_compute_telemetria', store=True, string='Nº de posiciones')
    distancia_recorrida_km = fields.Float(
        compute='_compute_telemetria', store=True, string='Distancia recorrida (km)', digits=(10, 3),
        help='Suma de tramos Haversine entre posiciones válidas ordenadas por fecha GPS.')
    velocidad_maxima_kmh = fields.Float(compute='_compute_telemetria', store=True, string='Velocidad máxima (km/h)')
    velocidad_media_kmh = fields.Float(compute='_compute_telemetria', store=True, string='Velocidad media (km/h)')

    @api.depends('posicion_ids', 'posicion_ids.latitud', 'posicion_ids.longitud',
                 'posicion_ids.valida', 'posicion_ids.velocidad_kmh', 'posicion_ids.fecha_gps')
    def _compute_telemetria(self):
        for rec in self:
            validas = rec.posicion_ids.filtered('valida').sorted(lambda p: (p.fecha_gps, p.id))
            rec.cantidad_posiciones = len(rec.posicion_ids)
            rec.distancia_recorrida_km = geo_utils.distancia_total_km(
                [(p.latitud, p.longitud) for p in validas])
            velocidades = validas.mapped('velocidad_kmh')
            rec.velocidad_maxima_kmh = max(velocidades) if velocidades else 0.0
            rec.velocidad_media_kmh = round(sum(velocidades) / len(velocidades), 2) if velocidades else 0.0

    def _procesar_geocercas(self, posiciones):
        """Marca como atendidas las paradas pendientes cuando una posición cae dentro de su radio.

        La hora de llegada es la del GPS (no la del procesamiento) para que el retraso sea fiel.
        """
        self.ensure_one()
        for pos in posiciones:
            for linea in self.parada_line_ids.filtered(lambda l: l.estado_parada == 'pendiente'):
                parada = linea.parada_id
                dist = geo_utils.haversine_m(pos.latitud, pos.longitud, parada.latitude, parada.longitude)
                if dist <= parada.radio_deteccion:
                    linea.write({
                        'estado_parada': 'atendida',
                        'hora_llegada_real': pos.fecha_gps,
                        'metodo_registro': 'gps',
                        'observaciones': _("Detectada por GPS a %.1f m del punto (radio %.0f m).")
                                         % (dist, parada.radio_deteccion),
                    })

    def action_ver_mapa_gps(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client', 'tag': 'transporte_gps_map',
            'name': _('Mapa GPS - %s') % self.name,
            'context': {'viaje_id': self.id},
        }

    def action_ver_posiciones(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Posiciones GPS'),
            'res_model': 'transporte.gps.posicion', 'view_mode': 'tree,form',
            'domain': [('viaje_id', '=', self.id)],
        }
