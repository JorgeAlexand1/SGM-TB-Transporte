# -*- coding: utf-8 -*-
import logging
import os
import time
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..lib import geo_utils, traccar_parser
from ..lib.traccar_client import TraccarClient, TraccarError
from .gps_posicion import verificar_gestor

_logger = logging.getLogger(__name__)

PARAM = 'transporte_gps.'


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    traccar_device_id = fields.Integer(
        string='ID de dispositivo Traccar', index=True, copy=False,
        help='Identificador numérico (id interno) del dispositivo en Traccar. 0 = sin GPS asociado.')
    ultima_posicion_id = fields.Many2one(
        'transporte.gps.posicion', string='Última posición válida', readonly=True, copy=False, ondelete='set null')
    ultima_posicion_fecha = fields.Datetime(related='ultima_posicion_id.fecha_gps', string='Última actualización GPS')
    ultima_latitud = fields.Float(related='ultima_posicion_id.latitud', string='Última latitud', digits=(10, 6))
    ultima_longitud = fields.Float(related='ultima_posicion_id.longitud', string='Última longitud', digits=(10, 6))
    ultima_velocidad_kmh = fields.Float(related='ultima_posicion_id.velocidad_kmh', string='Última velocidad (km/h)')
    estado_senal = fields.Selection(
        [('sin_datos', 'Sin datos'), ('con_senal', 'Con señal'), ('sin_senal', 'Sin señal / desactualizado')],
        string='Estado de señal GPS', default='sin_datos', readonly=True, copy=False)
    posicion_ids = fields.One2many('transporte.gps.posicion', 'vehicle_id', string='Posiciones GPS')
    posicion_count = fields.Integer(compute='_compute_posicion_count', string='Posiciones')

    _sql_constraints = [
        ('traccar_device_unique', 'EXCLUDE (traccar_device_id WITH =) WHERE (traccar_device_id > 0)',
         'Ese dispositivo Traccar ya está asociado a otro vehículo.'),
    ]

    def _compute_posicion_count(self):
        datos = self.env['transporte.gps.posicion'].read_group(
            [('vehicle_id', 'in', self.ids)], ['vehicle_id'], ['vehicle_id'])
        mapa = {d['vehicle_id'][0]: d['vehicle_id_count'] for d in datos}
        for rec in self:
            rec.posicion_count = mapa.get(rec.id, 0)

    @api.constrains('traccar_device_id')
    def _check_traccar_device_id(self):
        for rec in self:
            if rec.traccar_device_id < 0:
                raise ValidationError(_("El ID de dispositivo Traccar no puede ser negativo."))

    # ------------------------------------------------------------------ configuración
    @api.model
    def _gps_param(self, clave, default=None):
        return self.env['ir.config_parameter'].sudo().get_param(PARAM + clave, default)

    @api.model
    def _traccar_client(self):
        url = self._gps_param('traccar_url') or os.environ.get('TRACCAR_URL')
        if not url:
            raise TraccarError(_("Configure la URL de Traccar en Ajustes > Transporte GPS."))
        return TraccarClient(
            url, token=self._gps_param('traccar_token'),
            user=self._gps_param('traccar_user'), password=self._gps_param('traccar_password'))

    @api.model
    def _minutos_sin_senal(self):
        try:
            return int(self._gps_param('minutos_sin_senal', 5)) or 5
        except (TypeError, ValueError):
            return 5

    # ------------------------------------------------------------------ sincronización
    def _fecha_desde_sync(self):
        self.ensure_one()
        ultima = self.env['transporte.gps.posicion'].sudo().search(
            [('vehicle_id', '=', self.id), ('simulado', '=', False)], order='fecha_gps desc', limit=1)
        base = ultima.fecha_gps if ultima else fields.Datetime.now() - timedelta(days=1)
        # 1 min de solape: los duplicados se descartan por el UNIQUE y se evita perder tramas tardías
        return base - timedelta(minutes=1)

    def _sincronizar_traccar(self, origen='cron', client=None):
        """Trae las posiciones nuevas de un bus desde Traccar. Devuelve el log creado."""
        self.ensure_one()
        inicio = time.monotonic()
        log_vals = {'vehicle_id': self.id, 'origen': origen}
        try:
            client = client or self._traccar_client()
            desde = self._fecha_desde_sync()
            hasta = fields.Datetime.now() + timedelta(minutes=1)
            crudas = client.get_positions(
                self.traccar_device_id,
                traccar_parser.formato_fecha_api(desde),
                traccar_parser.formato_fecha_api(hasta))
            parseadas, malformadas = [], 0
            for raw in crudas:
                try:
                    parseadas.append(traccar_parser.parse_posicion(raw))
                except (ValueError, TypeError):
                    malformadas += 1
            res = self.env['transporte.gps.posicion'].sudo().registrar_posiciones(self, parseadas)
            self._procesar_posiciones_nuevas(res['nuevas'])
            log_vals.update(
                posiciones_traidas=len(crudas),
                posiciones_nuevas=len(res['nuevas']),
                duplicados_descartados=res['duplicadas'],
                posiciones_invalidas=res['invalidas'] + malformadas)
        except (TraccarError, ValueError) as exc:
            log_vals['error'] = str(exc)
            _logger.warning("Sync Traccar del bus %s falló: %s", self.display_name, exc)
        log_vals['duracion_ms'] = int((time.monotonic() - inicio) * 1000)
        return self.env['transporte.gps.sync.log'].sudo().create(log_vals)

    def action_sincronizar_traccar(self):
        for rec in self:
            if not rec.traccar_device_id:
                raise UserError(_("El bus '%s' no tiene dispositivo Traccar asociado.") % rec.display_name)
            log = rec._sincronizar_traccar('manual')
            if log.error:
                raise UserError(_("Sincronización fallida: %s") % log.error)
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': _('Sincronización Traccar'), 'type': 'success', 'sticky': False,
                       'message': _('Posiciones sincronizadas correctamente.')},
        }

    @api.model
    def procesar_webhook(self, parsed, inicio=None):
        """Registra una posición recibida por webhook. None si el dispositivo no está asociado a un bus."""
        verificar_gestor(self.env)
        inicio = inicio if inicio is not None else time.monotonic()
        bus = self.search([('traccar_device_id', '=', parsed['traccar_device_id'])], limit=1)
        if not bus:
            return None
        res = self.env['transporte.gps.posicion'].registrar_posiciones(bus, [parsed])
        bus._procesar_posiciones_nuevas(res['nuevas'])
        self.env['transporte.gps.sync.log'].sudo().create({
            'vehicle_id': bus.id, 'origen': 'webhook', 'posiciones_traidas': 1,
            'posiciones_nuevas': len(res['nuevas']), 'duplicados_descartados': res['duplicadas'],
            'posiciones_invalidas': res['invalidas'],
            'duracion_ms': int((time.monotonic() - inicio) * 1000),
        })
        return {'nuevas': len(res['nuevas']), 'duplicadas': res['duplicadas']}

    @api.model
    def _cron_sincronizar_traccar(self):
        buses = self.search([('traccar_device_id', '>', 0)])
        if not buses:
            return
        try:
            client = self._traccar_client()
        except TraccarError as exc:
            _logger.info("Sync Traccar omitida: %s", exc)
            return
        for bus in buses:
            try:  # H-B08: un fallo inesperado en un bus no detiene la sincronización del resto
                with self.env.cr.savepoint():
                    bus._sincronizar_traccar('cron', client)
            except Exception:  # noqa: BLE001 - se registra y se continúa con el siguiente bus
                _logger.exception("Sync Traccar del bus %s abortada por un error inesperado", bus.display_name)
        self._cron_actualizar_senal()

    # ------------------------------------------------------------------ procesamiento
    def _procesar_posiciones_nuevas(self, posiciones):
        """Asocia posiciones al viaje en curso, dispara geocercas y refresca la última posición."""
        self.ensure_one()
        if not posiciones:
            self._actualizar_estado_senal()
            return
        viaje = self.env['transporte.viaje'].sudo().search(
            [('vehicle_id', '=', self.id), ('state', '=', 'in_progress')], limit=1)
        if viaje and viaje.hora_salida_real:
            del_viaje = posiciones.filtered(lambda p: p.fecha_gps >= viaje.hora_salida_real)
            del_viaje.write({'viaje_id': viaje.id})
            viaje._procesar_geocercas(del_viaje.filtered('valida').sorted('fecha_gps'))
        # la ubicación "actual" del bus nunca debe salir de una posición simulada
        validas = self.env['transporte.gps.posicion'].sudo().search(
            [('vehicle_id', '=', self.id), ('valida', '=', True), ('simulado', '=', False)],
            order='fecha_gps desc, id desc', limit=1)
        if validas:
            self.sudo().write({'ultima_posicion_id': validas.id})
        self._actualizar_estado_senal()

    def _actualizar_estado_senal(self):
        ahora = fields.Datetime.now()
        limite = self._minutos_sin_senal()
        for rec in self:
            if not rec.ultima_posicion_id:
                nuevo = 'sin_datos'
            elif geo_utils.senal_desactualizada(rec.ultima_posicion_id.fecha_gps, ahora, limite):
                nuevo = 'sin_senal'
            else:
                nuevo = 'con_senal'
            if rec.estado_senal != nuevo:
                rec.sudo().write({'estado_senal': nuevo})

    @api.model
    def _cron_actualizar_senal(self):
        self.search([('traccar_device_id', '>', 0)])._actualizar_estado_senal()

    # ------------------------------------------------------------------ UI
    def action_ver_posiciones(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Posiciones GPS'),
            'res_model': 'transporte.gps.posicion', 'view_mode': 'tree,form',
            'domain': [('vehicle_id', '=', self.id)],
        }

    @api.model
    def get_datos_mapa(self, viaje_id=False):
        """Datos para el mapa Leaflet: última posición de cada bus y, si hay viaje, trazado y paradas."""
        buses = self.search([('traccar_device_id', '>', 0)])
        vehiculos = []
        for b in buses.filtered('ultima_posicion_id'):
            vehiculos.append({
                'id': b.id, 'nombre': b.display_name, 'placa': b.license_plate or '',
                'lat': b.ultima_latitud, 'lon': b.ultima_longitud,
                'velocidad': b.ultima_velocidad_kmh, 'fecha': fields.Datetime.to_string(b.ultima_posicion_fecha),
                'senal': b.estado_senal,
            })
        trazado, paradas = [], []
        if viaje_id:
            viaje = self.env['transporte.viaje'].browse(int(viaje_id)).exists()
            if viaje:
                pos = viaje.posicion_ids.filtered('valida').sorted('fecha_gps')
                trazado = [[p.latitud, p.longitud] for p in pos]
                paradas = [{
                    'nombre': l.parada_id.name, 'lat': l.parada_latitude, 'lon': l.parada_longitude,
                    'radio': l.parada_id.radio_deteccion, 'estado': l.estado_parada, 'secuencia': l.secuencia,
                } for l in viaje.parada_line_ids.sorted('secuencia')]
        return {'vehiculos': vehiculos, 'trazado': trazado, 'paradas': paradas}
