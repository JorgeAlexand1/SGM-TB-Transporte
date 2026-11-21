# -*- coding: utf-8 -*-
"""Prueba de integración EN VIVO contra un servidor Traccar real (A3/A9).

Recorre la cadena completa sin mocks:
  posiciones enviadas por el protocolo OsmAnd (el mismo de Traccar Client) -> Traccar Server ->
  API REST -> sincronización de Odoo (sin duplicados) -> geocercas (paradas «atendidas» por GPS) ->
  verificación de exactitud Traccar <-> Odoo.

No forma parte de la suite estándar (tag ``traccar_vivo``). La ejecuta ``scripts/prueba_integracion_traccar.sh``,
que levanta un Traccar efímero y pasa sus datos por variables de entorno; sin ellas la prueba se omite.
"""
import calendar
import os
import time
import unittest
import uuid
from datetime import timedelta

import requests

from odoo import fields
from odoo.tests.common import TransactionCase, tagged

ENV = ('TRACCAR_VIVO_URL', 'TRACCAR_VIVO_OSMAND', 'TRACCAR_VIVO_USER', 'TRACCAR_VIVO_PASSWORD')
# Paradas de prueba (Ambato) y minutos desde el origen
PARADAS = [(-1.238400, -78.621500, 0), (-1.242300, -78.625400, 4), (-1.247100, -78.629800, 8)]
TIMEOUT_S = 30


@tagged('post_install', '-at_install', '-standard', 'traccar_vivo')
class TestTraccarEnVivo(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        faltan = [v for v in ENV if not os.environ.get(v)]
        if faltan:
            raise unittest.SkipTest('Traccar en vivo no configurado (faltan %s)' % ', '.join(faltan))
        cls.url = os.environ['TRACCAR_VIVO_URL'].rstrip('/')
        cls.osmand = os.environ['TRACCAR_VIVO_OSMAND'].rstrip('/')
        cls.auth = (os.environ['TRACCAR_VIVO_USER'], os.environ['TRACCAR_VIVO_PASSWORD'])
        cls.unique_id = 'sgmtb-prueba-%s' % uuid.uuid4().hex[:10]
        resp = requests.post(cls.url + '/api/devices', json={'name': 'Bus prueba SGM-TB', 'uniqueId': cls.unique_id},
                             auth=cls.auth, timeout=15)
        resp.raise_for_status()
        cls.device_id = resp.json()['id']
        cls.addClassCleanup(lambda: requests.delete('%s/api/devices/%s' % (cls.url, cls.device_id),
                                                    auth=cls.auth, timeout=15))

        env = cls.env
        param = env['ir.config_parameter'].sudo()
        param.set_param('transporte_gps.traccar_url', cls.url)
        param.set_param('transporte_gps.traccar_user', cls.auth[0])
        param.set_param('transporte_gps.traccar_password', cls.auth[1])
        param.set_param('transporte_gps.traccar_token', '')
        param.set_param('transporte_gps.geocerca_modo', 'segmento')
        marca = env['fleet.vehicle.model.brand'].create({'name': 'Vivo'})
        modelo = env['fleet.vehicle.model'].create({'name': 'Vivo Bus', 'brand_id': marca.id})
        cls.bus = env['fleet.vehicle'].create({
            'model_id': modelo.id, 'license_plate': 'VIVO-001', 'es_bus_pasajeros': True,
            'capacidad_sentados': 30, 'capacidad_pie': 10, 'traccar_device_id': cls.device_id})
        ruta = env['transporte.ruta'].create({
            'name': 'Ruta vivo', 'codigo': 'VIVO-R1', 'tipo_ruta': 'urbana', 'tiempo_estimado_min': PARADAS[-1][2],
            'parada_ids': [(0, 0, {
                'parada_id': env['transporte.parada'].create({
                    'name': 'Vivo P%s' % i, 'codigo': 'VIVO-P%s' % i, 'latitude': lat, 'longitude': lon,
                    'radio_deteccion': 40}).id,
                'secuencia': i, 'tiempo_desde_origen_min': minuto})
                for i, (lat, lon, minuto) in enumerate(PARADAS, start=1)]})
        conductor = env['hr.employee'].create({
            'name': 'Vivo Conductor', 'es_conductor': True, 'licencia_nro': 'VIVO-LIC', 'licencia_categoria': 'tipo_d',
            'licencia_fecha_vencimiento': fields.Date.today() + timedelta(days=365)})
        # Salida hace 15 min: las posiciones se envían con hora pasada (Traccar descarta horas futuras)
        cls.salida = fields.Datetime.now().replace(microsecond=0) - timedelta(minutes=15)
        cls.viaje = env['transporte.viaje'].create({
            'ruta_id': ruta.id, 'vehicle_id': cls.bus.id, 'driver_id': conductor.id,
            'hora_salida_planificada': cls.salida,
            'hora_llegada_planificada': cls.salida + timedelta(minutes=PARADAS[-1][2])})
        cls.viaje.action_programar()
        cls.viaje.action_iniciar()
        cls.viaje.write({'hora_salida_real': cls.salida})

        # Un reporte sobre cada parada, 1 min después de su hora programada (como Traccar Client)
        cls.enviadas = []
        for lat, lon, minuto in PARADAS:
            fecha = cls.salida + timedelta(minutes=minuto + 1)
            r = requests.get(cls.osmand + '/', params={
                'id': cls.unique_id, 'lat': lat, 'lon': lon, 'speed': 10, 'valid': 'true',
                'timestamp': calendar.timegm(fecha.timetuple()),  # fechas de Odoo: UTC sin zona
            }, timeout=15)
            r.raise_for_status()
            cls.enviadas.append(fecha)
        cls.remotas = cls._esperar_posiciones(len(PARADAS))

    @classmethod
    def _esperar_posiciones(cls, n):
        desde = (cls.salida - timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        hasta = (fields.Datetime.now() + timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        limite = time.monotonic() + TIMEOUT_S
        while True:
            datos = requests.get(cls.url + '/api/positions', params={
                'deviceId': cls.device_id, 'from': desde, 'to': hasta}, auth=cls.auth, timeout=15).json()
            if len(datos) >= n or time.monotonic() > limite:
                return datos
            time.sleep(1)

    def test_01_traccar_recibio_lo_enviado_por_osmand(self):
        self.assertEqual(len(self.remotas), len(PARADAS))
        for raw, (lat, lon, _m) in zip(sorted(self.remotas, key=lambda p: p['fixTime']), PARADAS):
            self.assertAlmostEqual(raw['latitude'], lat, places=6)
            self.assertAlmostEqual(raw['longitude'], lon, places=6)

    def test_02_cadena_completa_traccar_odoo(self):
        log = self.bus._sincronizar_traccar('manual')
        self.assertFalse(log.error, log.error)
        self.assertEqual((log.posiciones_traidas, log.posiciones_nuevas), (len(PARADAS), len(PARADAS)))

        posiciones = self.env['transporte.gps.posicion'].search([('vehicle_id', '=', self.bus.id)], order='fecha_gps')
        self.assertEqual(posiciones.mapped('fecha_gps'), self.enviadas)  # hora GPS, no hora de recepción
        self.assertFalse(posiciones.filtered('simulado'))
        self.assertEqual(posiciones.mapped('viaje_id'), self.viaje)
        self.assertEqual(self.bus.ultima_posicion_id, posiciones[-1])

        # geocercas: las 3 paradas quedan atendidas por GPS con la hora del reporte
        lineas = self.viaje.parada_line_ids.sorted('secuencia')
        self.assertEqual(lineas.mapped('estado_parada'), ['atendida'] * len(PARADAS))
        self.assertEqual(set(lineas.mapped('metodo_registro')), {'gps'})
        self.assertEqual(lineas.mapped('hora_llegada_real'), self.enviadas)

        # re-sincronizar no duplica (solape de 1 min deliberado)
        log2 = self.bus._sincronizar_traccar('manual')
        self.assertEqual(log2.posiciones_nuevas, 0)
        self.assertGreaterEqual(log2.duplicados_descartados, 1)
        self.assertEqual(self.env['transporte.gps.posicion'].search_count([('vehicle_id', '=', self.bus.id)]),
                         len(PARADAS))

        # exactitud Traccar <-> Odoo con el servidor real
        res = self.env['transporte.calidad.dashboard'].verificar_exactitud_sync()
        self.assertEqual((res['verificadas'], res['iguales'], res['faltantes'], res['distintas']),
                         (len(PARADAS), len(PARADAS), 0, 0))
        self.assertEqual(res['valor'], 100.0)
