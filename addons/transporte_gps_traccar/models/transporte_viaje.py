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

    @api.model
    def _parametros_geocerca(self):
        """Modo de detección ('segmento' por defecto, 'punto' = comportamiento original) y tramo máximo (s)."""
        param = self.env['ir.config_parameter'].sudo()
        modo = param.get_param('transporte_gps.geocerca_modo', 'segmento')
        try:
            max_s = int(param.get_param('transporte_gps.geocerca_segmento_max_s', 360))
        except (TypeError, ValueError):
            max_s = 360
        return (modo if modo in ('punto', 'segmento') else 'segmento'), max_s

    def _procesar_geocercas(self, posiciones):
        """Marca como atendidas las paradas pendientes por las que pasó el bus.

        - Modo 'punto': una muestra GPS debe caer dentro del radio de la parada.
        - Modo 'segmento' (mejora PDCA): además se evalúa el tramo entre la muestra anterior y la
          actual; si el tramo cruza el radio se interpola la hora de paso. Evita falsas "paradas
          omitidas" cuando Traccar Client reporta con intervalos largos. No se interpola a través
          de huecos mayores que `geocerca_segmento_max_s` (pérdida de señal).

        La hora de llegada es la del GPS (no la del procesamiento) para que el retraso sea fiel.
        """
        self.ensure_one()
        if not posiciones:
            return
        modo, max_s = self._parametros_geocerca()
        previa = self.env['transporte.gps.posicion'].sudo().search([
            ('viaje_id', '=', self.id), ('valida', '=', True),
            ('fecha_gps', '<', posiciones[0].fecha_gps)], order='fecha_gps desc, id desc', limit=1)
        for pos in posiciones:
            usar_previa = bool(previa) and (pos.fecha_gps - previa.fecha_gps).total_seconds() <= max_s
            for linea in self.parada_line_ids.filtered(lambda l: l.estado_parada == 'pendiente'):
                parada = linea.parada_id
                detectada, dist, t = geo_utils.paso_por_radio(
                    parada.latitude, parada.longitude, parada.radio_deteccion,
                    (previa.latitud, previa.longitud) if usar_previa else None,
                    (pos.latitud, pos.longitud), modo)
                if not detectada:
                    continue
                if t < 1.0:
                    hora = previa.fecha_gps + (pos.fecha_gps - previa.fecha_gps) * t
                    obs = _("Detectada por GPS (tramo interpolado) a %.1f m del punto (radio %.0f m).")
                else:
                    hora = pos.fecha_gps
                    obs = _("Detectada por GPS a %.1f m del punto (radio %.0f m).")
                linea.write({
                    'estado_parada': 'atendida',
                    'hora_llegada_real': hora.replace(microsecond=0),
                    'metodo_registro': 'gps',
                    'observaciones': obs % (dist, parada.radio_deteccion),
                })
            previa = pos

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
