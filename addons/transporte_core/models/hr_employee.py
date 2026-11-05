# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    es_conductor = fields.Boolean(
        string='Es Conductor de Bus',
        default=False,
        help='Indica si el empleado está asignado al rol de conductor en la operación de transporte.'
    )
    licencia_nro = fields.Char(
        string='Número de Licencia',
        copy=False,
        help='Identificación oficial de la licencia de conducir profesional.'
    )
    licencia_categoria = fields.Selection(
        selection=[
            ('tipo_c', 'Tipo C (Taxis / Furgonetas)'),
            ('tipo_d', 'Tipo D (Buses de Pasajeros e Interprovinciales)'),
            ('tipo_e', 'Tipo E (Vehículos Pesados / Articulados)'),
            ('profesional_otra', 'Otra Categoría Profesional'),
        ],
        string='Categoría de Licencia',
        default='tipo_d',
        help='Tipo o clase de licencia profesional otorgada por la autoridad de tránsito.'
    )
    licencia_fecha_vencimiento = fields.Date(
        string='Fecha de Vencimiento de Licencia',
        help='Fecha de caducidad reglamentaria de la licencia de conducir.'
    )
    licencia_habilitada = fields.Boolean(
        string='Habilitado para Conducir',
        compute='_compute_licencia_habilitada',
        store=True,
        help='Indica si el conductor tiene su documentación completa y licencia vigente.'
    )

    @api.depends('es_conductor', 'licencia_nro', 'licencia_fecha_vencimiento')
    def _compute_licencia_habilitada(self):
        hoy = fields.Date.today()
        for record in self:
            if record.es_conductor and record.licencia_nro and record.licencia_fecha_vencimiento:
                record.licencia_habilitada = record.licencia_fecha_vencimiento >= hoy
            else:
                record.licencia_habilitada = False

    @api.constrains('es_conductor', 'licencia_nro', 'licencia_fecha_vencimiento')
    def _check_datos_conductor(self):
        hoy = fields.Date.today()
        for record in self:
            if record.es_conductor:
                if not record.licencia_nro or not record.licencia_nro.strip():
                    raise ValidationError(
                        "Para habilitar a un empleado como conductor de bus, es obligatorio ingresar el número de licencia."
                    )
                if not record.licencia_fecha_vencimiento:
                    raise ValidationError(
                        "Para habilitar a un empleado como conductor de bus, es obligatorio indicar la fecha de vencimiento de la licencia."
                    )
                if record.licencia_fecha_vencimiento < hoy:
                    raise ValidationError(
                        f"No se puede registrar al empleado como conductor con una licencia vencida ({record.licencia_fecha_vencimiento})."
                    )
