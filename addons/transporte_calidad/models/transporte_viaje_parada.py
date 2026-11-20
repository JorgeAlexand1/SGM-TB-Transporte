# -*- coding: utf-8 -*-
from odoo import api, fields, models


class TransporteViajeParada(models.Model):
    _inherit = 'transporte.viaje.parada'

    retraso_min = fields.Float(
        string='Retraso (min)', compute='_compute_retraso', store=True, digits=(10, 1), group_operator='avg',
        help='Hora real de llegada menos hora planificada. Negativo = llegó antes.')
    puntualidad = fields.Selection(
        [('pendiente', 'Pendiente'), ('puntual', 'Puntual'), ('atrasada', 'Atrasada'),
         ('adelantada', 'Adelantada'), ('omitida', 'Omitida')],
        string='Puntualidad', default='pendiente', readonly=True,
        help='Resultado de comparar el retraso con las tolerancias configuradas.')

    @api.depends('hora_llegada_real', 'hora_planificada')
    def _compute_retraso(self):
        for rec in self:
            if rec.hora_llegada_real and rec.hora_planificada:
                rec.retraso_min = round((rec.hora_llegada_real - rec.hora_planificada).total_seconds() / 60.0, 1)
            else:
                rec.retraso_min = 0.0
