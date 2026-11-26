# -*- coding: utf-8 -*-
import logging

from psycopg2 import IntegrityError

from odoo import _, api, fields, models
from odoo.exceptions import AccessError
from odoo.tools import mute_logger

_logger = logging.getLogger(__name__)

GRUPO_GESTOR = 'transporte_core.group_transporte_manager'


def verificar_gestor(env):
    """Autoriza operaciones que escriben datos de telemetría o mediciones (H-A03).

    Los métodos públicos son invocables por RPC por cualquier usuario autenticado y escriben con
    sudo(); solo se permiten a procesos internos (env.su: cron/webhook/código con sudo) o al grupo
    Administrador de Operaciones.
    """
    if not env.su and not env.user.has_group(GRUPO_GESTOR):
        raise AccessError(_('Solo el Administrador de Operaciones o un proceso interno puede '
                            'registrar posiciones GPS o mediciones.'))


class GpsPosicion(models.Model):
    _name = 'transporte.gps.posicion'
    _description = 'Posición GPS recibida de Traccar'
    _order = 'fecha_gps desc, id desc'

    traccar_position_id = fields.Integer(string='ID posición Traccar', required=True, index=True, readonly=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string='Bus', required=True, ondelete='cascade', index=True)
    viaje_id = fields.Many2one('transporte.viaje', string='Viaje', ondelete='set null', index=True)
    latitud = fields.Float(digits=(10, 6), required=True)
    longitud = fields.Float(digits=(10, 6), required=True)
    velocidad_kmh = fields.Float(string='Velocidad (km/h)', digits=(6, 2))
    fecha_gps = fields.Datetime(string='Fecha GPS (UTC)', required=True, index=True)
    valida = fields.Boolean(string='Válida', default=True,
                            help='False si Traccar marcó la posición como inválida o las coordenadas son (0,0)/fuera de rango.')
    simulado = fields.Boolean(string='Simulado', default=False,
                              help='Datos de prueba: nunca deben presentarse como reales.')

    _sql_constraints = [
        ('traccar_position_unique', 'unique(traccar_position_id)',
         'La posición de Traccar ya fue registrada (evita duplicados).'),
    ]

    @api.model
    def registrar_posiciones(self, vehicle, parsed_list, simulado=False):
        """Inserta posiciones parseadas sin duplicados.

        :return: dict con 'nuevas' (recordset), 'duplicadas' (int) e 'invalidas' (int)
        """
        verificar_gestor(self.env)
        vistos = set()
        unicos = []
        for p in parsed_list:
            if p['traccar_position_id'] not in vistos:
                vistos.add(p['traccar_position_id'])
                unicos.append(p)
        repetidas_lote = len(parsed_list) - len(unicos)
        existentes = set(self.sudo().search(
            [('traccar_position_id', 'in', list(vistos))]).mapped('traccar_position_id'))
        pendientes = [p for p in unicos if p['traccar_position_id'] not in existentes]
        duplicadas = repetidas_lote + len(unicos) - len(pendientes)

        nuevas = self.browse()
        for p in pendientes:
            vals = {
                'traccar_position_id': p['traccar_position_id'],
                'vehicle_id': vehicle.id,
                'latitud': p['latitud'],
                'longitud': p['longitud'],
                'velocidad_kmh': p['velocidad_kmh'],
                'fecha_gps': p['fecha_gps'],
                'valida': p['valida'],
                'simulado': simulado,
            }
            try:
                # savepoint: una carrera cron/webhook no debe abortar la transacción completa
                with self.env.cr.savepoint(), mute_logger('odoo.sql_db'):
                    nuevas |= self.sudo().create(vals)
            except IntegrityError:
                duplicadas += 1
        invalidas = len(nuevas.filtered(lambda r: not r.valida))
        return {'nuevas': nuevas, 'duplicadas': duplicadas, 'invalidas': invalidas}
