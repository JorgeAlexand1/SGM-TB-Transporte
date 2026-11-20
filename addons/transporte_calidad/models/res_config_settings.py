# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from ..lib.reglas import TOLERANCIAS_DEFECTO

PREFIJO = 'transporte_calidad.'


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cal_tol_retraso_min = fields.Float(
        string='Tolerancia de retraso (min)', default=TOLERANCIAS_DEFECTO['retraso_min'],
        config_parameter=PREFIJO + 'retraso_min',
        help='Una llegada hasta N minutos después de la hora programada se considera puntual.')
    cal_tol_adelanto_min = fields.Float(
        string='Tolerancia de adelanto (min)', default=TOLERANCIAS_DEFECTO['adelanto_min'],
        config_parameter=PREFIJO + 'adelanto_min',
        help='Llegar más de N minutos antes de lo programado se considera adelanto (pasajeros pierden el bus).')
    cal_ancho_corredor_m = fields.Float(
        string='Corredor por defecto (m)', default=TOLERANCIAS_DEFECTO['ancho_corredor_m'],
        config_parameter=PREFIJO + 'ancho_corredor_m',
        help='Distancia máxima al trazado de referencia; cada ruta puede definir el suyo.')
    cal_fuera_consecutivas = fields.Integer(
        string='Posiciones seguidas fuera del corredor', default=int(TOLERANCIAS_DEFECTO['fuera_consecutivas']),
        config_parameter=PREFIJO + 'fuera_consecutivas',
        help='Evita marcar como desvío un salto aislado del GPS.')
    cal_gap_senal_min = fields.Float(
        string='Hueco de señal (min)', default=TOLERANCIAS_DEFECTO['gap_senal_min'],
        config_parameter=PREFIJO + 'gap_senal_min',
        help='Tiempo sin posiciones durante el recorrido que se registra como pérdida de señal.')
    cal_tol_duracion_pct = fields.Float(
        string='Diferencia de duración tolerada (%)', default=TOLERANCIAS_DEFECTO['duracion_pct'],
        config_parameter=PREFIJO + 'duracion_pct')

    @api.constrains('cal_tol_retraso_min', 'cal_tol_adelanto_min', 'cal_ancho_corredor_m',
                    'cal_fuera_consecutivas', 'cal_gap_senal_min', 'cal_tol_duracion_pct')
    def _check_tolerancias(self):
        for rec in self:
            if min(rec.cal_tol_retraso_min, rec.cal_tol_adelanto_min, rec.cal_gap_senal_min,
                   rec.cal_tol_duracion_pct) < 0:
                raise ValidationError(_('Las tolerancias no pueden ser negativas.'))
            if rec.cal_ancho_corredor_m <= 0 or rec.cal_fuera_consecutivas < 1:
                raise ValidationError(_('El corredor debe ser > 0 m y se requiere al menos 1 posición fuera.'))

    def action_reevaluar_viajes(self):
        self.execute()
        n = self.env['transporte.viaje'].sudo()._reevaluar_todos()
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': _('Calidad del servicio'), 'type': 'success', 'sticky': False,
                       'message': _('%s viajes reevaluados con las tolerancias actuales.') % n},
        }
