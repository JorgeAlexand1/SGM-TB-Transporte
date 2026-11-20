# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

TIPOS = [
    ('retraso_inicio', 'Retraso en la salida'),
    ('retraso_parada', 'Retraso en parada'),
    ('adelanto_parada', 'Adelanto en parada'),
    ('retraso_llegada', 'Retraso en la llegada'),
    ('parada_omitida', 'Parada omitida'),
    ('recorrido_incompleto', 'Recorrido incompleto'),
    ('diferencia_tiempo', 'Diferencia tiempo estimado/real'),
    ('desviacion_ruta', 'Desviación de la ruta'),
    ('perdida_senal', 'Pérdida de señal GPS'),
    ('falla_mecanica', 'Falla mecánica'),
    ('accidente', 'Accidente / incidente vial'),
    ('queja_usuario', 'Queja de usuario'),
    ('otro', 'Otro'),
]


class TransporteIncidencia(models.Model):
    _name = 'transporte.incidencia'
    _description = 'Incidencia del Servicio de Transporte'
    _inherit = ['mail.thread']
    _order = 'fecha desc, id desc'

    name = fields.Char(string='Código', required=True, readonly=True, copy=False, default='/')
    fecha = fields.Datetime(string='Fecha', required=True, default=fields.Datetime.now, index=True, tracking=True)
    tipo = fields.Selection(TIPOS, string='Tipo', required=True, index=True, tracking=True)
    severidad = fields.Selection(
        [('baja', 'Baja'), ('media', 'Media'), ('alta', 'Alta'), ('critica', 'Crítica')],
        string='Severidad', required=True, default='media', tracking=True)
    estado = fields.Selection(
        [('abierta', 'Abierta'), ('en_atencion', 'En atención'), ('resuelta', 'Resuelta'),
         ('descartada', 'Descartada')], string='Estado', required=True, default='abierta', tracking=True)
    origen = fields.Selection(
        [('automatica', 'Detectada automáticamente'), ('manual', 'Registrada manualmente')],
        string='Origen', required=True, default='manual', readonly=True)
    viaje_id = fields.Many2one('transporte.viaje', string='Viaje', ondelete='cascade', index=True)
    viaje_parada_id = fields.Many2one('transporte.viaje.parada', string='Parada del viaje', ondelete='cascade')
    parada_id = fields.Many2one('transporte.parada', string='Parada', ondelete='set null')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Bus', ondelete='set null', index=True)
    ruta_id = fields.Many2one('transporte.ruta', string='Ruta', ondelete='set null', index=True)
    valor = fields.Float(string='Valor medido', digits=(10, 2))
    unidad = fields.Char(string='Unidad')
    descripcion = fields.Text(string='Descripción')
    regla = fields.Char(string='Regla aplicada', readonly=True)
    simulado = fields.Boolean(string='Simulado', related='viaje_id.simulado', store=True)
    fecha_dia = fields.Date(string='Día', compute='_compute_fecha_dia', store=True)

    @api.depends('fecha')
    def _compute_fecha_dia(self):
        for rec in self:
            rec.fecha_dia = fields.Date.to_date(fields.Datetime.context_timestamp(rec, rec.fecha)) if rec.fecha else False

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = seq.next_by_code('transporte.incidencia') or '/'
            if vals.get('viaje_id'):
                viaje = self.env['transporte.viaje'].browse(vals['viaje_id'])
                vals.setdefault('vehicle_id', viaje.vehicle_id.id)
                vals.setdefault('ruta_id', viaje.ruta_id.id)
        return super().create(vals_list)

    @api.onchange('viaje_id')
    def _onchange_viaje(self):
        if self.viaje_id:
            self.vehicle_id = self.viaje_id.vehicle_id
            self.ruta_id = self.viaje_id.ruta_id

    def unlink(self):
        if not self.env.context.get('reevaluacion') and any(r.origen == 'automatica' for r in self):
            raise UserError(_('Las incidencias detectadas automáticamente no se eliminan: márquelas como '
                              '"Descartada" para conservar la trazabilidad.'))
        return super().unlink()

    def action_atender(self):
        self.write({'estado': 'en_atencion'})

    def action_resolver(self):
        self.write({'estado': 'resuelta'})

    def action_descartar(self):
        self.write({'estado': 'descartada'})
