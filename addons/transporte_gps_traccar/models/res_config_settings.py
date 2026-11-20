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
    gps_geocerca_modo = fields.Selection(
        [('segmento', 'Tramo entre muestras (recomendado)'), ('punto', 'Solo muestra dentro del radio')],
        string='Detección de paradas', config_parameter='transporte_gps.geocerca_modo', default='segmento',
        help="'Tramo' también detecta la parada si el bus pasó por ella entre dos reportes GPS "
             "(intervalos largos de Traccar Client).")
    gps_geocerca_segmento_max_s = fields.Integer(
        string='Tramo máximo interpolable (s)', config_parameter='transporte_gps.geocerca_segmento_max_s',
        default=360, help='No se interpola a través de huecos mayores (pérdida de señal).')
