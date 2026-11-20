# -*- coding: utf-8 -*-
"""Asistente: genera los recorridos de prueba SIMULADOS de la actividad A5.

Usa el flujo real del sistema (programar -> posiciones -> geocerca -> finalizar -> evaluar), de modo
que lo que se prueba es la lógica de producción y no un atajo. Todo queda marcado `simulado=True`.
"""
from datetime import datetime, time as dtime, timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..lib import simulador

ZONA_DEFECTO = 'America/Guayaquil'


class TransporteCalidadSimulacion(models.TransientModel):
    _name = 'transporte.calidad.simulacion'
    _description = 'Generador de recorridos simulados'

    fecha_inicio = fields.Date(string='Primer día', required=True,
                               default=lambda self: fields.Date.context_today(self) - timedelta(days=1))
    dias = fields.Integer(string='Días a generar', required=True, default=1,
                          help='Cada día genera el plan de 10 recorridos (útil para comparar periodos).')
    ruta_ids = fields.Many2many('transporte.ruta', string='Rutas (3)', required=True,
                                default=lambda self: self.env['transporte.ruta'].search(
                                    [('total_paradas', '>=', 4)], limit=3))
    vehicle_ids = fields.Many2many('fleet.vehicle', string='Buses (2)', required=True,
                                   domain=[('es_bus_pasajeros', '=', True)],
                                   default=lambda self: self.env['fleet.vehicle'].search(
                                       [('es_bus_pasajeros', '=', True), ('capacidad_total', '>', 0)], limit=2))
    driver_id = fields.Many2one('hr.employee', string='Conductor', required=True,
                                domain=[('es_conductor', '=', True)],
                                default=lambda self: self.env['hr.employee'].search(
                                    [('es_conductor', '=', True), ('licencia_habilitada', '=', True)], limit=1))
    plan = fields.Text(string='Plan', readonly=True, default=lambda self: '\n'.join(
        '%2d. %-18s ruta %d · bus %d · %02d:%02d · cada %d s -> esperadas: %s' % (
            i + 1, e, r + 1, b + 1, h[0], h[1], s, ', '.join(sorted(simulador.ESCENARIOS[e][1])) or 'ninguna')
        for i, (e, r, b, h, s) in enumerate(simulador.PLAN_DIEZ)))

    @api.model
    def _siguiente_id_simulado(self):
        """Las posiciones simuladas usan ids negativos: nunca chocan con ids reales de Traccar."""
        self.env.cr.execute('SELECT LEAST(COALESCE(MIN(traccar_position_id), 0), 0) FROM transporte_gps_posicion')
        return self.env.cr.fetchone()[0] - 1

    def _a_utc(self, dia, hora_min):
        zona = pytz.timezone(self.env.user.tz or ZONA_DEFECTO)
        local = zona.localize(datetime.combine(dia, dtime(hora_min[0], hora_min[1])))
        return local.astimezone(pytz.utc).replace(tzinfo=None)

    def _validar(self):
        if len(self.ruta_ids) < 3:
            raise UserError(_('Seleccione 3 rutas.'))
        if len(self.vehicle_ids) < 2:
            raise UserError(_('Seleccione 2 buses.'))
        if self.dias < 1 or self.dias > 31:
            raise UserError(_('Genere entre 1 y 31 días.'))
        for ruta in self.ruta_ids:
            if ruta.total_paradas < 3:
                raise UserError(_('La ruta %s necesita al menos 3 paradas.') % ruta.name)
        for bus in self.vehicle_ids:
            if bus.estado_operativo != 'disponible':
                raise UserError(_('El bus %s debe estar Disponible para programar viajes.') % bus.display_name)

    def simular_viaje(self, ruta, bus, salida_plan, escenario, intervalo_s, semilla=0):
        """Crea, programa y ejecuta un viaje simulado. Devuelve el viaje evaluado."""
        Viaje = self.env['transporte.viaje']
        lineas_ruta = ruta.parada_ids.sorted('secuencia')
        llegada_plan = salida_plan + timedelta(minutes=max(ruta.tiempo_estimado_min,
                                                           lineas_ruta[-1].tiempo_desde_origen_min))
        descripcion, esperadas = simulador.ESCENARIOS[escenario]
        viaje = Viaje.create({
            'ruta_id': ruta.id, 'vehicle_id': bus.id, 'driver_id': self.driver_id.id,
            'fecha_viaje': fields.Date.to_date(fields.Datetime.context_timestamp(self, salida_plan)),
            'hora_salida_planificada': salida_plan, 'hora_llegada_planificada': llegada_plan,
            'notas': _('DATOS SIMULADOS - escenario "%s": %s') % (escenario, descripcion),
        })
        viaje.action_programar()
        sim = simulador.generar_recorrido(
            [{'lat': l.parada_id.latitude, 'lon': l.parada_id.longitude, 't_min': l.tiempo_desde_origen_min}
             for l in lineas_ruta], salida_plan, escenario, intervalo_s, semilla)
        viaje.write({'simulado': True, 'escenario_simulado': escenario,
                     'incidencias_esperadas': ', '.join(sorted(esperadas)) or 'ninguna',
                     'state': 'in_progress', 'hora_salida_real': sim['salida_real']})

        siguiente = self._siguiente_id_simulado()
        parsed = [{'traccar_position_id': siguiente - i, 'traccar_device_id': bus.traccar_device_id or 0,
                   'latitud': la, 'longitud': lo, 'velocidad_kmh': vel, 'fecha_gps': f, 'valida': True}
                  for i, (f, la, lo, vel) in enumerate(sim['puntos'])]
        res = self.env['transporte.gps.posicion'].registrar_posiciones(bus, parsed, simulado=True)
        res['nuevas'].write({'viaje_id': viaje.id})
        viaje._procesar_geocercas(res['nuevas'].sorted('fecha_gps'))

        pendientes = viaje.parada_line_ids.filtered(lambda l: l.estado_parada == 'pendiente')
        pendientes.write({'estado_parada': 'omitida'})
        viaje.write({'state': 'completed', 'hora_llegada_real': sim['llegada_real']})
        viaje._evaluar_calidad()
        return viaje

    def action_generar(self):
        self.ensure_one()
        self._validar()
        rutas, buses = self.ruta_ids.sorted('codigo')[:3], self.vehicle_ids.sorted('id')[:2]
        viajes = self.env['transporte.viaje']
        for d in range(self.dias):
            dia = self.fecha_inicio + timedelta(days=d)
            for n, (escenario, ri, bi, hora, intervalo) in enumerate(simulador.PLAN_DIEZ):
                viajes |= self.simular_viaje(rutas[ri], buses[bi], self._a_utc(dia, hora), escenario,
                                             intervalo, semilla=d * 100 + n)
        return {
            'type': 'ir.actions.act_window', 'name': _('Recorridos simulados generados'),
            'res_model': 'transporte.viaje', 'view_mode': 'tree,form',
            'domain': [('id', 'in', viajes.ids)], 'context': {'search_default_filter_hoy': 0},
        }
