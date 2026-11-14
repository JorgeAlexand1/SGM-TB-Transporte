# -*- coding: utf-8 -*-
"""Endpoint de recepción en tiempo real (forward de Traccar). Complementa al cron de sincronización."""
import hmac
import json
import logging
import os
import time

import odoo
from odoo import SUPERUSER_ID, api, http
from odoo.http import request

from ..lib import traccar_parser

_logger = logging.getLogger(__name__)


def _json(status, **body):
    return request.make_response(
        json.dumps(body), headers=[('Content-Type', 'application/json')], status=status)


def token_valido(cabecera, secreto):
    """Compara en tiempo constante el Bearer recibido contra el secreto configurado."""
    if not secreto or not cabecera or not cabecera.startswith('Bearer '):
        return False
    return hmac.compare_digest(cabecera[len('Bearer '):].encode(), secreto.encode())


class TraccarWebhook(http.Controller):

    @http.route('/api/v1/traccar/webhook', type='http', auth='none', methods=['POST'], csrf=False)
    def webhook(self, db=None, **kwargs):
        """Traccar (forward.url + forward.json=true) -> POST con {"position": {...}, "device": {...}}.

        Autenticación: cabecera `Authorization: Bearer <secreto>`; la BD se indica con ?db=<nombre>.
        """
        inicio = time.monotonic()
        db = db or http.db_monodb()
        if not db:
            return _json(400, error='Parámetro db requerido')
        try:
            payload = json.loads(request.httprequest.get_data(as_text=True) or '{}')
            parsed = traccar_parser.parse_payload_forward(payload)
        except ValueError as exc:
            return _json(400, error='Payload inválido: %s' % exc)

        with odoo.registry(db).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            param = env['ir.config_parameter']
            secreto = param.get_param('transporte_gps.webhook_secret') or os.environ.get('TRACCAR_WEBHOOK_SECRET')
            if not token_valido(request.httprequest.headers.get('Authorization'), secreto):
                return _json(401, error='No autorizado')
            resultado = env['fleet.vehicle'].procesar_webhook(parsed, inicio)
            if resultado is None:
                return _json(404, error='Dispositivo %s no asociado a ningún bus' % parsed['traccar_device_id'])
            cr.commit()
            return _json(200, **resultado)
