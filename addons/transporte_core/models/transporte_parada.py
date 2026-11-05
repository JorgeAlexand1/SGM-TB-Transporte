# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class TransporteParada(models.Model):
    _name = 'transporte.parada'
    _description = 'Parada de Bus Georreferenciada'
    _order = 'name asc'

    name = fields.Char(
        string='Nombre de la Parada',
        required=True,
        index=True,
        help='Denominación común de la parada (ej. Terminal Norte, Plaza Central).'
    )
    codigo = fields.Char(
        string='Código Único',
        required=True,
        index=True,
        copy=False,
        help='Identificador alfanumérico único de la parada (ej. PAR-001).'
    )
    latitude = fields.Float(
        string='Latitud',
        digits=(10, 6),
        required=True,
        help='Coordenada de latitud en formato decimal (WGS84, entre -90 y 90).'
    )
    longitude = fields.Float(
        string='Longitud',
        digits=(10, 6),
        required=True,
        help='Coordenada de longitud en formato decimal (WGS84, entre -180 y 180).'
    )
    radio_deteccion = fields.Float(
        string='Radio de Detección (m)',
        default=35.0,
        required=True,
        help='Radio geodésico en metros para determinar la llegada del bus a la parada.'
    )
    active = fields.Boolean(
        string='Activo',
        default=True,
        help='Permite archivar la parada en lugar de eliminarla del sistema.'
    )

    _sql_constraints = [
        ('codigo_unique', 'unique(codigo)', 'El código de la parada debe ser único.')
    ]

    @api.constrains('codigo')
    def _check_codigo_unique(self):
        for record in self:
            if record.codigo:
                duplicados = self.search_count([
                    ('codigo', '=ilike', record.codigo.strip()),
                    ('id', '!=', record.id)
                ])
                if duplicados > 0:
                    raise ValidationError(
                        f"El código de parada '{record.codigo}' ya se encuentra registrado. Debe ser único."
                    )

    @api.constrains('latitude', 'longitude')
    def _check_coordenadas(self):
        for record in self:
            if not (-90.0 <= record.latitude <= 90.0):
                raise ValidationError(
                    f"Latitud inválida ({record.latitude}). Debe estar comprendida entre -90.0 y 90.0 grados."
                )
            if not (-180.0 <= record.longitude <= 180.0):
                raise ValidationError(
                    f"Longitud inválida ({record.longitude}). Debe estar comprendida entre -180.0 y 180.0 grados."
                )

    @api.constrains('radio_deteccion')
    def _check_radio_deteccion(self):
        for record in self:
            if record.radio_deteccion <= 0.0:
                raise ValidationError(
                    f"El radio de detección ({record.radio_deteccion} m) debe ser estrictamente mayor a 0 metros."
                )
