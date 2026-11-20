# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    traccar_url = fields.Char(
        string='URL de Traccar', config_parameter='transporte_gps.traccar_url',
        help='URL base de la API de Traccar, p. ej. https://traccar.midominio.com')
    traccar_token = fields.Char(
        string='Token de API', config_parameter='transporte_gps.traccar_token',
        help='Token Bearer de Traccar (Cuenta > Token). Tiene prioridad sobre usuario/contraseña.')
    traccar_user = fields.Char(string='Usuario Traccar', config_parameter='transporte_gps.traccar_user')
    traccar_password = fields.Char(string='Contraseña Traccar', config_parameter='transporte_gps.traccar_password')
    gps_minutos_sin_senal = fields.Integer(
        string='Minutos para marcar sin señal', config_parameter='transporte_gps.minutos_sin_senal', default=5)
    gps_webhook_secret = fields.Char(
        string='Secreto del webhook', config_parameter='transporte_gps.webhook_secret',
        help='Token Bearer que debe enviar Traccar al endpoint /api/v1/traccar/webhook.')
