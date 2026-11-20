# -*- coding: utf-8 -*-
"""Cliente mínimo de la API REST de Traccar (devices, positions)."""
import requests


class TraccarError(Exception):
    """Error de comunicación o autenticación con Traccar."""


class TraccarClient(object):
    def __init__(self, base_url, token=None, user=None, password=None, timeout=15):
        if not base_url:
            raise TraccarError("URL de Traccar no configurada")
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.headers = {'Accept': 'application/json'}
        self.auth = None
        if token:
            self.headers['Authorization'] = 'Bearer %s' % token
        elif user:
            self.auth = (user, password or '')

    def _get(self, path, params=None):
        try:
            resp = requests.get(self.base_url + path, params=params, headers=self.headers,
                                auth=self.auth, timeout=self.timeout)
        except requests.RequestException as exc:
            raise TraccarError("No se pudo conectar con Traccar: %s" % exc)
        if resp.status_code in (401, 403):
            raise TraccarError("Credenciales rechazadas por Traccar (HTTP %s)" % resp.status_code)
        if resp.status_code != 200:
            raise TraccarError("Traccar respondió HTTP %s" % resp.status_code)
        try:
            return resp.json()
        except ValueError:
            raise TraccarError("Respuesta de Traccar no es JSON válido")

    def get_devices(self):
        return self._get('/api/devices')

    def get_positions(self, device_id, desde, hasta):
        """Historial de posiciones. `desde`/`hasta` ya en formato ISO (ver traccar_parser.formato_fecha_api)."""
        return self._get('/api/positions', {'deviceId': device_id, 'from': desde, 'to': hasta})

    def get_ultima_posicion(self, device_id):
        datos = self._get('/api/positions', {'deviceId': device_id})
        return datos[0] if datos else None
