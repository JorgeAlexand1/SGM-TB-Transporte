# -*- coding: utf-8 -*-
import json
from datetime import timedelta
from unittest import mock

from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import HttpCase, TransactionCase, tagged
from odoo.tools import mute_logger

from ..lib.traccar_client import TraccarError

LAT0, LON0 = -1.240000, -78.620000
LAT1, LON1 = -1.245000, -78.625000


def raw_pos(pid, device, lat, lon, fecha, speed=10.0, valid=True):
    return {
        'id': pid, 'deviceId': device, 'latitude': lat, 'longitude': lon, 'speed': speed,
        'valid': valid, 'fixTime': fecha.strftime('%Y-%m-%dT%H:%M:%S.000+00:00'),
    }


class GpsCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        brand = env['fleet.vehicle.model.brand'].create({'name': 'GPSBrand'})
        modelo = env['fleet.vehicle.model'].create({'name': 'GPS Bus', 'brand_id': brand.id})
        cls.bus = env['fleet.vehicle'].create({
            'model_id': modelo.id, 'license_plate': 'GPS-001', 'es_bus_pasajeros': True,
            'capacidad_sentados': 30, 'capacidad_pie': 10, 'traccar_device_id': 901})
        cls.bus2 = env['fleet.vehicle'].create({
            'model_id': modelo.id, 'license_plate': 'GPS-002', 'es_bus_pasajeros': True,
            'capacidad_sentados': 30, 'capacidad_pie': 10})
        cls.p1 = env['transporte.parada'].create({
            'name': 'GPS P1', 'codigo': 'GPS-P1', 'latitude': LAT0, 'longitude': LON0, 'radio_deteccion': 50})
        cls.p2 = env['transporte.parada'].create({
            'name': 'GPS P2', 'codigo': 'GPS-P2', 'latitude': LAT1, 'longitude': LON1, 'radio_deteccion': 50})
        ruta = env['transporte.ruta'].create({
            'name': 'GPS Ruta', 'codigo': 'GPS-R1', 'tipo_ruta': 'urbana', 'tiempo_estimado_min': 20})
        env['transporte.ruta.parada'].create({
            'ruta_id': ruta.id, 'parada_id': cls.p1.id, 'secuencia': 1, 'tiempo_desde_origen_min': 0})
        env['transporte.ruta.parada'].create({
            'ruta_id': ruta.id, 'parada_id': cls.p2.id, 'secuencia': 2, 'tiempo_desde_origen_min': 10})
        conductor = env['hr.employee'].create({
            'name': 'GPS Conductor', 'es_conductor': True, 'licencia_nro': 'GPS-LIC',
            'licencia_categoria': 'tipo_d',
            'licencia_fecha_vencimiento': fields.Date.today() + timedelta(days=365)})
        salida = fields.Datetime.now() - timedelta(minutes=5)
        cls.viaje = env['transporte.viaje'].create({
            'ruta_id': ruta.id, 'vehicle_id': cls.bus.id, 'driver_id': conductor.id,
            'hora_salida_planificada': salida, 'hora_llegada_planificada': salida + timedelta(minutes=20)})
        cls.viaje.action_programar()
        cls.viaje.action_iniciar()
        cls.t0 = cls.viaje.hora_salida_real

    def _sync(self, crudas):
        client = mock.Mock()
        client.get_positions.return_value = crudas
        return self.bus._sincronizar_traccar('manual', client=client)


@tagged('post_install', '-at_install')
class TestSincronizacion(GpsCommon):

    def test_01_sync_inserta_y_loguea(self):
        log = self._sync([raw_pos(1, 901, LAT0, LON0, self.t0 + timedelta(seconds=30))])
        self.assertTrue(log.ok)
        self.assertEqual((log.posiciones_traidas, log.posiciones_nuevas, log.duplicados_descartados), (1, 1, 0))
        self.assertEqual(self.env['transporte.gps.posicion'].search_count([('vehicle_id', '=', self.bus.id)]), 1)
        self.assertGreaterEqual(log.duracion_ms, 0)

    def test_02_tres_sincronizaciones_cero_duplicados(self):
        """RNF: 0 posiciones duplicadas tras 3 sincronizaciones."""
        crudas = [raw_pos(i, 901, LAT0, LON0, self.t0 + timedelta(seconds=10 * i)) for i in range(1, 6)]
        logs = [self._sync(crudas) for _ in range(3)]
        self.assertEqual(logs[0].posiciones_nuevas, 5)
        self.assertEqual([lg.posiciones_nuevas for lg in logs[1:]], [0, 0])
        self.assertEqual([lg.duplicados_descartados for lg in logs[1:]], [5, 5])
        self.assertEqual(self.env['transporte.gps.posicion'].search_count([('vehicle_id', '=', self.bus.id)]), 5)

    def test_03_duplicados_dentro_del_mismo_lote(self):
        r = raw_pos(10, 901, LAT0, LON0, self.t0 + timedelta(seconds=5))
        log = self._sync([r, dict(r)])
        self.assertEqual((log.posiciones_nuevas, log.duplicados_descartados), (1, 1))

    def test_04_unique_en_base_de_datos(self):
        Pos = self.env['transporte.gps.posicion']
        vals = {'traccar_position_id': 500, 'vehicle_id': self.bus.id, 'latitud': LAT0, 'longitud': LON0,
                'fecha_gps': self.t0}
        Pos.create(vals)
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'), self.env.cr.savepoint():
            Pos.create(vals)

    def test_05_posicion_invalida_se_guarda_pero_no_cuenta(self):
        crudas = [raw_pos(20, 901, 0, 0, self.t0 + timedelta(seconds=5)),
                  raw_pos(21, 901, LAT0, LON0, self.t0 + timedelta(seconds=10), valid=False)]
        log = self._sync(crudas)
        self.assertEqual(log.posiciones_invalidas, 2)
        self.assertFalse(self.bus.ultima_posicion_id)
        self.assertEqual(self.bus.estado_senal, 'sin_datos')
        self.assertEqual(self.viaje.distancia_recorrida_km, 0)

    def test_06_payload_malformado_se_descarta_sin_romper(self):
        log = self._sync([{'id': 30}, raw_pos(31, 901, LAT0, LON0, self.t0 + timedelta(seconds=5))])
        self.assertTrue(log.ok)
        self.assertEqual(log.posiciones_nuevas, 1)
        self.assertEqual(log.posiciones_invalidas, 1)

    def test_07_error_de_traccar_queda_en_el_log(self):
        client = mock.Mock()
        client.get_positions.side_effect = TraccarError('Credenciales rechazadas')
        log = self.bus._sincronizar_traccar('cron', client=client)
        self.assertFalse(log.ok)
        self.assertIn('Credenciales', log.error)

    def test_08_boton_manual_sin_dispositivo(self):
        with self.assertRaises(UserError):
            self.bus2.action_sincronizar_traccar()

    def test_09_dispositivo_traccar_unico(self):
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'), self.env.cr.savepoint():
            self.bus2.traccar_device_id = 901
            self.bus2.flush_recordset()

    def test_10_dispositivo_negativo_rechazado(self):
        with self.assertRaises(ValidationError):
            self.bus2.traccar_device_id = -1


@tagged('post_install', '-at_install')
class TestViajeYGeocercas(GpsCommon):

    def test_01_posiciones_se_asocian_al_viaje_en_curso(self):
        self._sync([raw_pos(1, 901, LAT0, LON0, self.t0 + timedelta(seconds=10))])
        self.assertEqual(self.viaje.cantidad_posiciones, 1)

    def test_02_posicion_anterior_a_la_salida_no_se_asocia(self):
        self._sync([raw_pos(2, 901, LAT0, LON0, self.t0 - timedelta(minutes=2))])
        self.assertEqual(self.viaje.cantidad_posiciones, 0)

    def test_03_geocerca_registra_llegada_con_hora_gps(self):
        fecha = self.t0 + timedelta(minutes=1)
        self._sync([raw_pos(3, 901, LAT0, LON0, fecha)])
        linea = self.viaje.parada_line_ids.filtered(lambda l: l.secuencia == 1)
        self.assertEqual(linea.estado_parada, 'atendida')
        self.assertEqual(linea.metodo_registro, 'gps')
        self.assertEqual(linea.hora_llegada_real, fecha.replace(microsecond=0))

    def test_04_fuera_de_radio_no_marca(self):
        # ~80 m al norte con radio 50 m
        self._sync([raw_pos(4, 901, LAT0 + 80 / 111195.0, LON0, self.t0 + timedelta(minutes=1))])
        self.assertEqual(self.viaje.parada_line_ids.mapped('estado_parada'), ['pendiente', 'pendiente'])

    def test_05_parada_atendida_no_se_sobrescribe(self):
        primera = self.t0 + timedelta(minutes=1)
        self._sync([raw_pos(5, 901, LAT0, LON0, primera), raw_pos(6, 901, LAT0, LON0, primera + timedelta(minutes=2))])
        linea = self.viaje.parada_line_ids.filtered(lambda l: l.secuencia == 1)
        self.assertEqual(linea.hora_llegada_real, primera.replace(microsecond=0))

    def test_06_recorrido_completo_distancia_y_velocidad(self):
        self._sync([
            raw_pos(7, 901, LAT0, LON0, self.t0 + timedelta(minutes=1), speed=5),
            raw_pos(8, 901, LAT1, LON1, self.t0 + timedelta(minutes=5), speed=20),
        ])
        self.assertEqual(set(self.viaje.parada_line_ids.mapped('estado_parada')), {'atendida'})
        self.assertAlmostEqual(self.viaje.distancia_recorrida_km, 0.785, delta=0.01)
        self.assertEqual(self.viaje.velocidad_maxima_kmh, 37.04)
        self.assertEqual(self.viaje.velocidad_media_kmh, 23.15)

    def test_07_viaje_finalizado_conserva_telemetria(self):
        self._sync([raw_pos(9, 901, LAT0, LON0, self.t0 + timedelta(minutes=1))])
        self.viaje.action_completar()
        self.assertEqual(self.viaje.cantidad_posiciones, 1)

    def test_08_sin_viaje_en_curso_solo_actualiza_ultima_posicion(self):
        self.viaje.action_completar()
        self._sync([raw_pos(40, 901, LAT0, LON0, fields.Datetime.now())])
        self.assertEqual(self.bus.ultima_latitud, LAT0)
        self.assertFalse(self.env['transporte.gps.posicion'].search([('traccar_position_id', '=', 40)]).viaje_id)

    def test_09_datos_para_el_mapa(self):
        self._sync([raw_pos(41, 901, LAT0, LON0, fields.Datetime.now())])
        datos = self.env['fleet.vehicle'].get_datos_mapa(self.viaje.id)
        self.assertEqual(len(datos['vehiculos']), 1)
        self.assertEqual(len(datos['trazado']), 1)
        self.assertEqual(len(datos['paradas']), 2)
        self.assertEqual(self.env['fleet.vehicle'].get_datos_mapa()['trazado'], [])


@tagged('post_install', '-at_install')
class TestSenal(GpsCommon):

    def test_01_con_senal(self):
        self._sync([raw_pos(50, 901, LAT0, LON0, fields.Datetime.now() - timedelta(minutes=1))])
        self.assertEqual(self.bus.estado_senal, 'con_senal')

    def test_02_sin_senal_por_datos_desactualizados(self):
        self._sync([raw_pos(51, 901, LAT0, LON0, fields.Datetime.now() - timedelta(minutes=10))])
        self.assertEqual(self.bus.estado_senal, 'sin_senal')

    def test_03_umbral_configurable(self):
        self.env['ir.config_parameter'].set_param('transporte_gps.minutos_sin_senal', '15')
        self._sync([raw_pos(52, 901, LAT0, LON0, fields.Datetime.now() - timedelta(minutes=10))])
        self.assertEqual(self.bus.estado_senal, 'con_senal')

    def test_04_cron_degrada_a_sin_senal(self):
        self._sync([raw_pos(53, 901, LAT0, LON0, fields.Datetime.now() - timedelta(minutes=1))])
        self.bus.ultima_posicion_id.fecha_gps = fields.Datetime.now() - timedelta(minutes=30)
        self.env['fleet.vehicle']._cron_actualizar_senal()
        self.assertEqual(self.bus.estado_senal, 'sin_senal')

    def test_05_sin_datos_al_inicio(self):
        self.assertEqual(self.bus2.estado_senal, 'sin_datos')

    def test_06_cron_sin_url_no_falla(self):
        self.env['ir.config_parameter'].set_param('transporte_gps.traccar_url', '')
        with mock.patch.dict('os.environ', {}, clear=False):
            self.env['fleet.vehicle']._cron_sincronizar_traccar()


@tagged('post_install', '-at_install')
class TestWebhook(HttpCase, GpsCommon):

    def _post(self, payload, token='s3creto', db=True):
        url = '/api/v1/traccar/webhook' + ('?db=%s' % self.env.cr.dbname if db else '')
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer %s' % token
        return self.url_open(url, data=json.dumps(payload), headers=headers)

    def setUp(self):
        super().setUp()
        self.env['ir.config_parameter'].set_param('transporte_gps.webhook_secret', 's3creto')
        self.env.cr.flush()

    def test_01_rechaza_sin_token(self):
        pos = raw_pos(59, 901, LAT0, LON0, fields.Datetime.now())
        self.assertEqual(self._post({'position': pos}, token=None).status_code, 401)

    def test_02_rechaza_token_incorrecto(self):
        pos = raw_pos(60, 901, LAT0, LON0, fields.Datetime.now())
        self.assertEqual(self._post({'position': pos}, token='malo').status_code, 401)

    def test_03_payload_invalido(self):
        self.assertEqual(self._post({'position': {'id': 1}}).status_code, 400)
