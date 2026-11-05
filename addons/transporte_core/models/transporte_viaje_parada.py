# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class TransporteViajeParada(models.Model):
    _name = 'transporte.viaje.parada'
    _description = 'Control de Parada en Viaje de Bus'
    _order = 'viaje_id asc, secuencia asc'

    viaje_id = fields.Many2one(
        comodel_name='transporte.viaje',
        string='Viaje',
        required=True,
        ondelete='cascade',
        index=True
    )
    parada_id = fields.Many2one(
        comodel_name='transporte.parada',
        string='Parada',
        required=True,
        ondelete='restrict',
        index=True
    )
    secuencia = fields.Integer(
        string='Secuencia',
        required=True,
        help='Orden correlativo de atención de la parada en este viaje.'
    )
    tiempo_desde_origen_min = fields.Integer(
        string='Tiempo Estimado desde Origen (min)',
        default=0,
        help='Instantánea histórica de los minutos previstos desde el origen de la ruta.'
    )
    hora_planificada = fields.Datetime(
        string='Hora Planificada',
        required=True,
        help='Fecha y hora programada para el arribo a esta parada.'
    )
    hora_llegada_real = fields.Datetime(
        string='Hora Real de Llegada',
        readonly=True,
        help='Fecha y hora exacta en la que se registró el arribo a la parada.'
    )
    estado_parada = fields.Selection(
        selection=[
            ('pendiente', 'Pendiente'),
            ('atendida', 'Atendida / Visitada'),
            ('omitida', 'Omitida / No Visitada'),
        ],
        string='Estado de Atención',
        default='pendiente',
        required=True,
        help='Situación operativa de la parada en el recorrido.'
    )
    metodo_registro = fields.Selection(
        selection=[
            ('manual', 'Manual (Operador/Despachador)'),
            ('gps', 'Automático (GPS Traccar)'),
        ],
        string='Método de Registro',
        default='manual',
        help='Vía por la cual se capturó la llegada del bus a la parada.'
    )
    observaciones = fields.Char(
        string='Observaciones Operativas',
        help='Anotaciones puntuales (ej. congestión en parada, desvío de carril, etc.).'
    )

    parada_codigo = fields.Char(
        related='parada_id.codigo',
        string='Código',
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
        ('viaje_secuencia_unique', 'unique(viaje_id, secuencia)',
         'No se puede repetir el número de secuencia de parada dentro del mismo viaje.')
    ]

    @api.constrains('viaje_id', 'secuencia')
    def _check_secuencia_unica_viaje(self):
        for record in self:
            if record.viaje_id and record.secuencia:
                duplicados = self.search([
                    ('id', '!=', record.id),
                    ('viaje_id', '=', record.viaje_id.id),
                    ('secuencia', '=', record.secuencia)
                ])
                if duplicados:
                    raise ValidationError(
                        f"La secuencia {record.secuencia} ya está asignada a otra parada en este mismo viaje."
                    )

    def action_registrar_llegada_manual(self):
        """Registra manualmente el arribo a la parada durante un viaje en curso."""
        for record in self:
            if record.viaje_id.state != 'in_progress':
                raise UserError(
                    "Solo se puede registrar la llegada en viajes que estén actualmente en estado 'En Ruta'."
                )
            if record.estado_parada == 'atendida':
                raise UserError(
                    f"La parada '{record.parada_id.name}' ya fue registrada como atendida a las {record.hora_llegada_real}."
                )
            if record.estado_parada == 'omitida':
                raise UserError(
                    f"La parada '{record.parada_id.name}' se encuentra marcada como omitida y no puede ser registrada."
                )

            record.write({
                'hora_llegada_real': fields.Datetime.now(),
                'estado_parada': 'atendida',
                'metodo_registro': 'manual',
            })

