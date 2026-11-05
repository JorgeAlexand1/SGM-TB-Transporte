# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class TransporteViaje(models.Model):
    _name = 'transporte.viaje'
    _description = 'Viaje y Despacho Operativo de Bus'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'hora_salida_planificada desc, id desc'

    name = fields.Char(
        string='Código de Despacho',
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('transporte.viaje') or '/',
        index=True
    )
    ruta_id = fields.Many2one(
        comodel_name='transporte.ruta',
        string='Línea / Ruta',
        required=True,
        ondelete='restrict',
        tracking=True,
        help='Recorrido oficial asignado para este viaje.'
    )
    vehicle_id = fields.Many2one(
        comodel_name='fleet.vehicle',
        string='Bus Asignado',
        required=True,
        ondelete='restrict',
        tracking=True,
        help='Unidad de transporte de pasajeros asignada al despacho.'
    )
    driver_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Conductor Asignado',
        required=True,
        ondelete='restrict',
        tracking=True,
        help='Conductor profesional con licencia vigente a cargo del bus.'
    )
    fecha_viaje = fields.Date(
        string='Fecha del Viaje',
        default=fields.Date.context_today,
        required=True,
        tracking=True
    )
    hora_salida_planificada = fields.Datetime(
        string='Salida Planificada',
        required=True,
        tracking=True,
        help='Fecha y hora programada para la partida desde la primera parada.'
    )
    hora_llegada_planificada = fields.Datetime(
        string='Llegada Planificada',
        required=True,
        tracking=True,
        help='Fecha y hora estimada para el fin del recorrido.'
    )
    hora_salida_real = fields.Datetime(
        string='Salida Real',
        readonly=True,
        tracking=True,
        help='Fecha y hora exacta en la que se despachó el viaje.'
    )
    hora_llegada_real = fields.Datetime(
        string='Llegada Real',
        readonly=True,
        tracking=True,
        help='Fecha y hora exacta en la que se completó el viaje.'
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Borrador'),
            ('scheduled', 'Programado'),
            ('in_progress', 'En Ruta'),
            ('completed', 'Completado'),
            ('cancelled', 'Cancelado'),
        ],
        string='Estado del Viaje',
        default='draft',
        required=True,
        tracking=True
    )
    parada_line_ids = fields.One2many(
        comodel_name='transporte.viaje.parada',
        inverse_name='viaje_id',
        string='Control de Paradas del Recorrido',
        copy=False
    )
    notas = fields.Text(
        string='Observaciones Operativas'
    )

    total_paradas_viaje = fields.Integer(
        string='Total Paradas',
        compute='_compute_estadisticas_paradas',
        store=True
    )
    paradas_atendidas = fields.Integer(
        string='Paradas Atendidas',
        compute='_compute_estadisticas_paradas',
        store=True
    )

    @api.depends('parada_line_ids', 'parada_line_ids.estado_parada')
    def _compute_estadisticas_paradas(self):
        for record in self:
            record.total_paradas_viaje = len(record.parada_line_ids)
            record.paradas_atendidas = len(record.parada_line_ids.filtered(lambda p: p.estado_parada == 'atendida'))

    @api.onchange('ruta_id', 'hora_salida_planificada')
    def _onchange_ruta_o_salida(self):
        """Calcula automáticamente la hora de llegada prevista a partir del tiempo estimado de la ruta."""
        if self.ruta_id and self.hora_salida_planificada and self.ruta_id.tiempo_estimado_min > 0:
            self.hora_llegada_planificada = self.hora_salida_planificada + timedelta(
                minutes=self.ruta_id.tiempo_estimado_min
            )

    @api.constrains('hora_salida_planificada', 'hora_llegada_planificada')
    def _check_horarios(self):
        for record in self:
            if record.hora_salida_planificada and record.hora_llegada_planificada:
                if record.hora_llegada_planificada <= record.hora_salida_planificada:
                    raise ValidationError(
                        "La hora de llegada planificada debe ser estrictamente posterior a la hora de salida planificada."
                    )

    @api.constrains('driver_id')
    def _check_conductor_elegible(self):
        for viaje in self:
            if viaje.driver_id:
                if not viaje.driver_id.es_conductor:
                    raise ValidationError(
                        f"El empleado '{viaje.driver_id.name}' no está registrado con funciones de conductor de bus."
                    )
                if not viaje.driver_id.licencia_habilitada:
                    raise ValidationError(
                        f"El conductor '{viaje.driver_id.name}' no cuenta con una licencia vigente y habilitada para conducir."
                    )

    @api.constrains('vehicle_id')
    def _check_bus_elegible(self):
        for viaje in self:
            if viaje.vehicle_id:
                if not viaje.vehicle_id.es_bus_pasajeros:
                    raise ValidationError(
                        f"El vehículo '{viaje.vehicle_id.name}' no está identificado como bus de transporte de pasajeros."
                    )
                if viaje.vehicle_id.capacidad_total <= 0:
                    raise ValidationError(
                        f"El bus '{viaje.vehicle_id.name}' tiene capacidad total igual a 0. Revise su configuración de aforo."
                    )

    def _check_conflictos_horarios(self):
        """Valida que ni el bus ni el conductor estén asignados a otros viajes en horarios superpuestos."""
        for record in self:
            if record.state == 'cancelled':
                continue

            # Rango horario a evaluar: [hora_salida_planificada, hora_llegada_planificada]
            # Condición de solapamiento: (Salida_A < Llegada_B) y (Llegada_A > Salida_B)
            # 1. Conflicto para el Bus
            conflictos_bus = self.search([
                ('id', '!=', record.id),
                ('vehicle_id', '=', record.vehicle_id.id),
                ('state', 'in', ['scheduled', 'in_progress']),
                ('hora_salida_planificada', '<', record.hora_llegada_planificada),
                ('hora_llegada_planificada', '>', record.hora_salida_planificada),
            ])
            if conflictos_bus:
                otro = conflictos_bus[0]
                raise ValidationError(
                    f"Conflicto de horario: El bus '{record.vehicle_id.name}' ({record.vehicle_id.license_plate}) "
                    f"ya está asignado al viaje '{otro.name}' programado entre {otro.hora_salida_planificada} "
                    f"y {otro.hora_llegada_planificada}."
                )

            # 2. Conflicto para el Conductor
            conflictos_conductor = self.search([
                ('id', '!=', record.id),
                ('driver_id', '=', record.driver_id.id),
                ('state', 'in', ['scheduled', 'in_progress']),
                ('hora_salida_planificada', '<', record.hora_llegada_planificada),
                ('hora_llegada_planificada', '>', record.hora_salida_planificada),
            ])
            if conflictos_conductor:
                otro = conflictos_conductor[0]
                raise ValidationError(
                    f"Conflicto de horario: El conductor '{record.driver_id.name}' "
                    f"ya está asignado al viaje '{otro.name}' programado entre {otro.hora_salida_planificada} "
                    f"y {otro.hora_llegada_planificada}."
                )

    def action_programar(self):
        """Valida requisitos operativos, genera paradas históricas y programa el viaje."""
        for record in self:
            if record.state != 'draft':
                raise UserError("Solo se pueden programar viajes en estado Borrador.")

            # Validar ruta con paradas
            if not record.ruta_id.parada_ids:
                raise ValidationError(
                    f"La ruta '{record.ruta_id.name}' no tiene paradas configuradas. No se puede despachar un viaje vacío."
                )

            # Validar bus
            if not record.vehicle_id.es_bus_pasajeros:
                raise ValidationError(
                    f"El vehículo '{record.vehicle_id.name}' no está identificado como bus de transporte de pasajeros."
                )
            if record.vehicle_id.capacidad_total <= 0:
                raise ValidationError(
                    f"El bus '{record.vehicle_id.name}' tiene capacidad total igual a 0. Revise su configuración de aforo."
                )
            if record.vehicle_id.estado_operativo != 'disponible':
                raise ValidationError(
                    f"El bus '{record.vehicle_id.name}' no está disponible (Estado actual: {record.vehicle_id.estado_operativo})."
                )

            # Validar conductor y licencia
            if not record.driver_id.es_conductor:
                raise ValidationError(
                    f"El empleado '{record.driver_id.name}' no está registrado con funciones de conductor de bus."
                )
            if not record.driver_id.licencia_nro:
                raise ValidationError(
                    f"El conductor '{record.driver_id.name}' no tiene un número de licencia profesional registrado."
                )
            if not record.driver_id.licencia_fecha_vencimiento:
                raise ValidationError(
                    f"El conductor '{record.driver_id.name}' no tiene fecha de vencimiento de licencia registrada."
                )
            if record.driver_id.licencia_fecha_vencimiento < record.fecha_viaje:
                raise ValidationError(
                    f"La licencia del conductor '{record.driver_id.name}' estará vencida ({record.driver_id.licencia_fecha_vencimiento}) "
                    f"para la fecha programada del viaje ({record.fecha_viaje})."
                )

            # Validar ausencia de conflictos de horario
            record._check_conflictos_horarios()

            # Generar instantánea de paradas
            record.parada_line_ids.unlink()
            lineas = []
            for p in record.ruta_id.parada_ids.sorted('secuencia'):
                hora_parada = record.hora_salida_planificada + timedelta(minutes=p.tiempo_desde_origen_min)
                lineas.append((0, 0, {
                    'parada_id': p.parada_id.id,
                    'secuencia': p.secuencia,
                    'tiempo_desde_origen_min': p.tiempo_desde_origen_min,
                    'hora_planificada': hora_parada,
                    'estado_parada': 'pendiente',
                    'metodo_registro': 'manual',
                }))
            record.write({
                'parada_line_ids': lineas,
                'state': 'scheduled',
            })

    def action_iniciar(self):
        """Inicia el recorrido del bus, marcándolo como en servicio."""
        for record in self:
            if record.state != 'scheduled':
                raise UserError("Solo se pueden iniciar viajes que estén en estado 'Programado'.")

            # Re-verificar vigencia de licencia al momento del inicio
            hoy = fields.Date.today()
            if record.driver_id.licencia_fecha_vencimiento < hoy:
                raise ValidationError(
                    f"No se puede iniciar el viaje: la licencia del conductor '{record.driver_id.name}' se encuentra vencida a la fecha de hoy."
                )

            # Re-verificar disponibilidad del bus
            if record.vehicle_id.estado_operativo not in ['disponible', 'en_servicio']:
                raise ValidationError(
                    f"No se puede iniciar el viaje: el bus '{record.vehicle_id.name}' se encuentra en estado '{record.vehicle_id.estado_operativo}'."
                )

            # Asignar hora de salida real y cambiar estados
            record.write({
                'hora_salida_real': fields.Datetime.now(),
                'state': 'in_progress',
            })
            record.vehicle_id.write({'estado_operativo': 'en_servicio'})

    def action_completar(self):
        """Finaliza el viaje, liberando el bus a estado disponible únicamente si estaba en servicio."""
        for record in self:
            if record.state != 'in_progress':
                raise UserError("Solo se pueden completar viajes que estén actualmente 'En Ruta'.")

            # Marcar paradas que quedaron pendientes como omitidas
            pendientes = record.parada_line_ids.filtered(lambda p: p.estado_parada == 'pendiente')
            if pendientes:
                pendientes.write({'estado_parada': 'omitida'})

            record.write({
                'hora_llegada_real': fields.Datetime.now(),
                'state': 'completed',
            })
            # Preservar el estado del bus si fue colocado en mantenimiento o fuera de servicio durante el viaje
            if record.vehicle_id.estado_operativo == 'en_servicio':
                record.vehicle_id.write({'estado_operativo': 'disponible'})

    def action_cancelar(self):
        """Cancela el viaje y libera el bus si estaba en ruta o programado."""
        for record in self:
            if record.state in ['completed']:
                raise UserError("No se puede cancelar un viaje que ya ha sido completado.")

            # Si estaba en servicio, restaurar bus a disponible
            if record.vehicle_id.estado_operativo == 'en_servicio':
                record.vehicle_id.write({'estado_operativo': 'disponible'})

            # Marcar paradas no atendidas como omitidas
            pendientes = record.parada_line_ids.filtered(lambda p: p.estado_parada == 'pendiente')
            if pendientes:
                pendientes.write({'estado_parada': 'omitida'})

            record.write({'state': 'cancelled'})

    def action_borrador(self):
        """Permite restablecer a borrador un viaje cancelado para reprogramarlo."""
        for record in self:
            if record.state != 'cancelled':
                raise UserError("Solo se pueden restablecer a borrador viajes cancelados.")
            record.parada_line_ids.unlink()
            record.write({
                'state': 'draft',
                'hora_salida_real': False,
                'hora_llegada_real': False,
            })

    def write(self, vals):
        """Protege la integridad operativa de viajes completados."""
        for record in self:
            if record.state == 'completed':
                campos_bloqueados = [
                    'ruta_id', 'vehicle_id', 'driver_id',
                    'hora_salida_planificada', 'hora_llegada_planificada',
                    'hora_salida_real', 'hora_llegada_real'
                ]
                if any(campo in vals for campo in campos_bloqueados):
                    raise UserError(
                        "No se pueden modificar los datos operativos de un viaje que ya ha sido completado."
                    )
        return super().write(vals)

    def unlink(self):
        """Impide eliminar viajes programados, en ruta o completados."""
        for record in self:
            if record.state not in ['draft', 'cancelled']:
                raise UserError(
                    f"No se puede eliminar el viaje '{record.name}' porque se encuentra en estado '{record.state}'. "
                    "Solo se pueden eliminar viajes en estado Borrador o Cancelado."
                )
        return super().unlink()

