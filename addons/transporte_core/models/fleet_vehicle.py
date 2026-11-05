# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    es_bus_pasajeros = fields.Boolean(
        string='Es Bus de Transporte',
        default=True,
        help='Indica si este vehículo de la flota está destinado al servicio de transporte de pasajeros.'
    )
    capacidad_sentados = fields.Integer(
        string='Pasajeros Sentados',
        default=0,
        help='Número de asientos disponibles para pasajeros sentados.'
    )
    capacidad_pie = fields.Integer(
        string='Pasajeros de Pie',
        default=0,
        help='Capacidad de aforo reglamentario para pasajeros de pie.'
    )
    capacidad_total = fields.Integer(
        string='Capacidad Total de Pasajeros',
        compute='_compute_capacidad_total',
        store=True,
        help='Aforo máximo del bus (suma de pasajeros sentados y de pie).'
    )
    tipo_bus = fields.Selection(
        selection=[
            ('microbus', 'Microbús (< 30 pasajeros)'),
            ('padron', 'Padrón Estándar (30 - 60 pasajeros)'),
            ('articulado', 'Articulado (60 - 120 pasajeros)'),
            ('biarticulado', 'Biarticulado (> 120 pasajeros)'),
        ],
        string='Tipo de Bus',
        default='padron',
        help='Clasificación técnica de la unidad según su capacidad y configuración de chasis.'
    )
    estado_operativo = fields.Selection(
        selection=[
            ('disponible', 'Disponible / Operativo'),
            ('en_servicio', 'En Servicio / En Ruta'),
            ('mantenimiento', 'En Mantenimiento / Taller'),
            ('fuera_servicio', 'Fuera de Servicio'),
        ],
        string='Estado Operativo de Transporte',
        default='disponible',
        required=True,
        tracking=True,
        help='Disponibilidad inmediata del bus para asignación de viajes y despachos.'
    )

    @api.depends('capacidad_sentados', 'capacidad_pie')
    def _compute_capacidad_total(self):
        for record in self:
            record.capacidad_total = record.capacidad_sentados + record.capacidad_pie

    @api.constrains('capacidad_sentados', 'capacidad_pie', 'es_bus_pasajeros')
    def _check_capacidades(self):
        for record in self:
            if record.capacidad_sentados < 0:
                raise ValidationError(
                    f"La capacidad de pasajeros sentados ({record.capacidad_sentados}) no puede ser negativa."
                )
            if record.capacidad_pie < 0:
                raise ValidationError(
                    f"La capacidad de pasajeros de pie ({record.capacidad_pie}) no puede ser negativa."
                )
            if record.es_bus_pasajeros and (record.capacidad_sentados + record.capacidad_pie) <= 0:
                raise ValidationError(
                    "Un bus destinado al transporte de pasajeros debe tener una capacidad total mayor a 0."
                )
