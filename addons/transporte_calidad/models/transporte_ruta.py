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
