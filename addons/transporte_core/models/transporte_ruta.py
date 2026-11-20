# -*- coding: utf-8 -*-
import math

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class TransporteRuta(models.Model):
    _name = 'transporte.ruta'
    _description = 'Ruta de Transporte en Buses'
    _order = 'name asc'

    name = fields.Char(
        string='Nombre de la Ruta',
        required=True,
        index=True,
        help='Denominación de la línea o ruta (ej. Línea 01 - Troncal Norte-Sur).'
    )
    codigo = fields.Char(
        string='Código de Línea',
        required=True,
        index=True,
        copy=False,
        help='Identificador único de la ruta (ej. RUT-001, L01).'
    )
    tipo_ruta = fields.Selection(
        selection=[
            ('urbana', 'Urbana'),
            ('troncal', 'Troncal'),
            ('alimentadora', 'Alimentadora'),
            ('interurbana', 'Interurbana'),
        ],
        string='Tipo de Ruta',
        default='urbana',
        required=True,
        help='Clasificación operativa de la ruta dentro de la red de transporte.'
    )
    descripcion = fields.Text(
        string='Descripción del Trazado',
        help='Detalles del recorrido, puntos de referencia o advertencias operativas.'
    )
    tiempo_estimado_min = fields.Integer(
        string='Tiempo Estimado Total (min)',
        default=0,
        required=True,
        help='Duración estimada del recorrido completo en minutos.'
    )
    active = fields.Boolean(
        string='Activo',
        default=True,
        help='Permite archivar la ruta si deja de operar temporal o permanentemente.'
    )
    parada_ids = fields.One2many(
        comodel_name='transporte.ruta.parada',
        inverse_name='ruta_id',
        string='Paradas de la Ruta',
        copy=True,
        help='Secuencia ordenada de paradas que componen esta ruta.'
    )
    total_paradas = fields.Integer(
        string='Total de Paradas',
        compute='_compute_total_paradas',
        store=True,
        help='Número de paradas registradas en el trazado de la ruta.'
    )
    origen_parada_id = fields.Many2one(
        comodel_name='transporte.parada',
        string='Origen',
        compute='_compute_origen_destino',
        store=True,
        help='Primera parada de la secuencia (menor número de secuencia).'
    )
    destino_parada_id = fields.Many2one(
        comodel_name='transporte.parada',
        string='Destino',
        compute='_compute_origen_destino',
        store=True,
        help='Última parada de la secuencia (mayor número de secuencia).'
    )
    distancia_estimada_km = fields.Float(
        string='Distancia Estimada (km)',
        digits=(10, 3),
        default=0.0,
        help='Longitud prevista del recorrido completo por calles, en kilómetros. '
             'Se compara contra la distancia recorrida por GPS.'
    )

    _sql_constraints = [
        ('codigo_unique', 'unique(codigo)', 'El código de la ruta debe ser único.')
    ]

    @api.depends('parada_ids')
    def _compute_total_paradas(self):
        for record in self:
            record.total_paradas = len(record.parada_ids)

    @api.depends('parada_ids', 'parada_ids.secuencia', 'parada_ids.parada_id')
    def _compute_origen_destino(self):
        for record in self:
            ordenadas = record.parada_ids.sorted('secuencia')
            record.origen_parada_id = ordenadas[:1].parada_id
            record.destino_parada_id = ordenadas[-1:].parada_id

    def _distancia_lineal_paradas_km(self):
        """Suma Haversine de los tramos rectos entre paradas consecutivas (cota inferior de la distancia real)."""
        self.ensure_one()
        total_m = 0.0
        puntos = [(p.parada_id.latitude, p.parada_id.longitude) for p in self.parada_ids.sorted('secuencia')]
        for (la1, lo1), (la2, lo2) in zip(puntos, puntos[1:]):
            p1, p2 = math.radians(la1), math.radians(la2)
            dphi, dlmb = p2 - p1, math.radians(lo2 - lo1)
            a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
            total_m += 2 * 6371008.8 * math.asin(min(1.0, math.sqrt(a)))
        return round(total_m / 1000.0, 3)

    def action_sugerir_distancia(self):
        """Propone la distancia estimada como la suma de tramos entre paradas (el usuario puede ajustarla)."""
        for record in self:
            record.distancia_estimada_km = record._distancia_lineal_paradas_km()

    @api.constrains('distancia_estimada_km')
    def _check_distancia_estimada(self):
        for record in self:
            if record.distancia_estimada_km < 0:
                raise ValidationError(
                    f"La distancia estimada ({record.distancia_estimada_km} km) no puede ser negativa."
                )

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
                        f"El código de ruta '{record.codigo}' ya se encuentra registrado. Debe ser único."
                    )

    @api.constrains('tiempo_estimado_min')
    def _check_tiempo_estimado(self):
        for record in self:
            if record.tiempo_estimado_min < 0:
                raise ValidationError(
                    f"El tiempo estimado ({record.tiempo_estimado_min} min) no puede ser negativo."
                )


class TransporteRutaParada(models.Model):
    _name = 'transporte.ruta.parada'
    _description = 'Asociación Secuencial Ruta - Parada'
    _order = 'ruta_id asc, secuencia asc'

    ruta_id = fields.Many2one(
        comodel_name='transporte.ruta',
        string='Ruta',
        required=True,
        ondelete='cascade',
        index=True
    )
    parada_id = fields.Many2one(
        comodel_name='transporte.parada',
        string='Parada',
        required=True,
        ondelete='restrict',
        index=True,
        help='Parada física asociada a este punto del recorrido.'
    )
    secuencia = fields.Integer(
        string='Secuencia',
        default=10,
        required=True,
        help='Orden correlativo de la parada en el sentido de la ruta.'
    )
    tiempo_desde_origen_min = fields.Integer(
        string='Tiempo Estimado desde Origen (min)',
        default=0,
        required=True,
        help='Minutos transcurridos previstos desde la parada inicial hasta este punto.'
    )

    parada_codigo = fields.Char(
        related='parada_id.codigo',
        string='Código Parada',
        readonly=True
    )
    parada_latitude = fields.Float(
        related='parada_id.latitude',
        string='Latitud',
        readonly=True,
        digits=(10, 6)
    )
    parada_longitude = fields.Float(
        related='parada_id.longitude',
        string='Longitud',
        readonly=True,
        digits=(10, 6)
    )

    _sql_constraints = [
        (
            'ruta_secuencia_unique',
            'unique(ruta_id, secuencia)',
            'No se permite repetir el número de secuencia dentro de la misma ruta.'
        )
    ]

    @api.constrains('secuencia')
    def _check_secuencia(self):
        for record in self:
            if record.secuencia < 1:
                raise ValidationError("El número de secuencia debe ser un entero positivo (mayor o igual a 1).")

    @api.constrains('ruta_id', 'secuencia')
    def _check_secuencia_unique(self):
        for record in self:
            if record.ruta_id and record.secuencia:
                duplicados = self.search_count([
                    ('ruta_id', '=', record.ruta_id.id),
                    ('secuencia', '=', record.secuencia),
                    ('id', '!=', record.id)
                ])
                if duplicados > 0:
                    raise ValidationError(
                        f"El número de secuencia {record.secuencia} ya está asignado a otra parada en esta ruta."
                    )

    @api.constrains('tiempo_desde_origen_min')
    def _check_tiempo_desde_origen(self):
        for record in self:
            if record.tiempo_desde_origen_min < 0:
                raise ValidationError(
                    f"El tiempo desde el origen ({record.tiempo_desde_origen_min} min) no puede ser negativo."
                )
