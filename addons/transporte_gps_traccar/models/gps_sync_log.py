# -*- coding: utf-8 -*-
from odoo import api, fields, models


class GpsSyncLog(models.Model):
    _name = 'transporte.gps.sync.log'
    _description = 'Registro de sincronización Traccar'
    _order = 'fecha desc, id desc'

    fecha = fields.Datetime(default=fields.Datetime.now, required=True, index=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string='Bus', ondelete='set null')
    origen = fields.Selection([('cron', 'Cron'), ('manual', 'Manual'), ('webhook', 'Webhook')],
                              default='cron', required=True)
    posiciones_traidas = fields.Integer(string='Posiciones recibidas')
    posiciones_nuevas = fields.Integer(string='Nuevas')
    duplicados_descartados = fields.Integer(string='Duplicados descartados')
    posiciones_invalidas = fields.Integer(string='Inválidas')
    duracion_ms = fields.Integer(string='Duración (ms)')
    error = fields.Text()
    ok = fields.Boolean(string='Correcta', compute='_compute_ok', store=True)

    @api.depends('error')
    def _compute_ok(self):
        for rec in self:
            rec.ok = not rec.error
