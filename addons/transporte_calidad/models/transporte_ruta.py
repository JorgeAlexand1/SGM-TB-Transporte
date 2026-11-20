# -*- coding: utf-8 -*-
import json

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class TransporteRuta(models.Model):
    _inherit = 'transporte.ruta'

    ancho_corredor_m = fields.Float(
        string='Corredor permitido (m)', default=0.0,
        help='Distancia máxima permitida al trazado de referencia antes de considerar desvío. '
             '0 = usar el valor global de Ajustes.')
    trazado_referencia = fields.Text(
        string='Trazado de referencia (JSON)', copy=False,
        help='Lista [[lat, lon], ...] del recorrido de referencia por calles. Si está vacío, '
             'se usa la polilínea que une las paradas en orden.')
    trazado_puntos = fields.Integer(string='Puntos del trazado', compute='_compute_trazado_puntos')
    trazado_origen = fields.Char(string='Origen del trazado', readonly=True, copy=False)
    viaje_ids = fields.One2many('transporte.viaje', 'ruta_id', string='Viajes')
    viajes_evaluados = fields.Integer(string='Recorridos evaluados', compute='_compute_indicadores_ruta')
    cumplimiento_pct = fields.Float(string='% cumplimiento', compute='_compute_indicadores_ruta', digits=(5, 1))
    puntualidad_pct = fields.Float(string='% puntualidad', compute='_compute_indicadores_ruta', digits=(5, 1))

    @api.depends('viaje_ids.resultado', 'viaje_ids.cumple_ruta', 'viaje_ids.paradas_puntuales',
                 'viaje_ids.paradas_atendidas')
    def _compute_indicadores_ruta(self):
        """Resumen histórico por ruta (todos los recorridos evaluados, reales y simulados)."""
        grupos = self.env['transporte.viaje'].read_group(
            [('ruta_id', 'in', self.ids), ('resultado', 'in', ('cumple', 'incumple'))],
            ['ruta_id', 'paradas_puntuales:sum', 'paradas_atendidas:sum'], ['ruta_id', 'cumple_ruta'], lazy=False)
        datos = {}
        for g in grupos:
            d = datos.setdefault(g['ruta_id'][0], {'n': 0, 'ok': 0, 'punt': 0, 'aten': 0})
            d['n'] += g['__count']
            d['ok'] += g['__count'] if g['cumple_ruta'] else 0
            d['punt'] += g['paradas_puntuales'] or 0
            d['aten'] += g['paradas_atendidas'] or 0
        for rec in self:
            d = datos.get(rec.id, {'n': 0, 'ok': 0, 'punt': 0, 'aten': 0})
            rec.viajes_evaluados = d['n']
            rec.cumplimiento_pct = 100.0 * d['ok'] / d['n'] if d['n'] else 0.0
            rec.puntualidad_pct = 100.0 * d['punt'] / d['aten'] if d['aten'] else 0.0

    @api.model
    def get_mapa_rutas(self):
        """Datos para el mapa de rutas: paradas en orden, trazado usado para detectar desvíos e indicadores."""
        corredor_global = float(self.env['ir.config_parameter'].sudo().get_param(
            'transporte_calidad.ancho_corredor_m', 150))
        return [{
            'id': r.id, 'codigo': r.codigo, 'nombre': r.name,
            'distancia': r.distancia_estimada_km, 'tiempo': r.tiempo_estimado_min,
            'corredor': r.ancho_corredor_m or corredor_global,
            'trazado_real': bool(r.trazado_referencia),
            'trazado': [list(p) for p in r._trazado_evaluacion()],
            'paradas': [{'secuencia': l.secuencia, 'nombre': l.parada_id.name, 'codigo': l.parada_id.codigo,
                         'lat': l.parada_id.latitude, 'lon': l.parada_id.longitude,
                         'radio': l.parada_id.radio_deteccion, 'min': l.tiempo_desde_origen_min}
                        for l in r.parada_ids.sorted('secuencia')],
            'evaluados': r.viajes_evaluados,
            'cumplimiento': round(r.cumplimiento_pct, 1),
            'puntualidad': round(r.puntualidad_pct, 1),
        } for r in self.search([])]

    @api.depends('trazado_referencia')
    def _compute_trazado_puntos(self):
        for rec in self:
            rec.trazado_puntos = len(rec._leer_trazado_json())

    def _leer_trazado_json(self):
        self.ensure_one()
        if not self.trazado_referencia:
            return []
        try:
            datos = json.loads(self.trazado_referencia)
            return [(float(p[0]), float(p[1])) for p in datos]
        except (ValueError, TypeError, IndexError):
            return []

    @api.constrains('trazado_referencia')
    def _check_trazado(self):
        for rec in self:
            if rec.trazado_referencia and len(rec._leer_trazado_json()) < 2:
                raise ValidationError(_('El trazado de referencia debe ser un JSON [[lat, lon], ...] con al menos 2 puntos.'))

    @api.constrains('ancho_corredor_m')
    def _check_ancho_corredor(self):
        for rec in self:
            if rec.ancho_corredor_m < 0:
                raise ValidationError(_('El corredor permitido no puede ser negativo.'))

    def _trazado_evaluacion(self):
        """Trazado usado para detectar desvíos: el de referencia o, en su defecto, la polilínea de paradas."""
        self.ensure_one()
        return self._leer_trazado_json() or [
            (p.parada_id.latitude, p.parada_id.longitude) for p in self.parada_ids.sorted('secuencia')]

    def action_limpiar_trazado(self):
        self.write({'trazado_referencia': False, 'trazado_origen': False})
