# -*- coding: utf-8 -*-
"""Pruebas de integración del módulo transporte_calidad (caja negra + caja blanca sobre Odoo).

Los identificadores CP-xx remiten a docs/PLAN_PRUEBAS.md.
"""
from datetime import datetime, timedelta
from unittest import mock

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user, tagged

# Paradas en Ambato (mismas coordenadas que DEMO-RUT-01/02/03)
P = {
    1: (-1.238400, -78.621500, 35), 2: (-1.242300, -78.625400, 30), 3: (-1.247100, -78.629800, 40),
    4: (-1.251500, -78.633200, 30), 5: (-1.256000, -78.637500, 35), 6: (-1.261200, -78.641000, 45),
    7: (-1.268500, -78.647000, 50), 8: (-1.244000, -78.612000, 40), 9: (-1.250500, -78.618500, 35),
    10: (-1.258000, -78.624000, 30), 11: (-1.233000, -78.628000, 40), 12: (-1.272000, -78.652000, 50),
}
RUTAS = {
    'TCAL-R1': [(1, 0), (2, 8), (3, 16), (4, 23), (5, 30), (6, 38), (7, 45)],
    'TCAL-R2': [(8, 0), (9, 7), (3, 15), (5, 22), (10, 29), (7, 35)],
    'TCAL-R3': [(11, 0), (1, 9), (9, 20), (6, 31), (12, 40)],
}
ID_BASE = 1_500_000_000


@tagged('post_install', '-at_install')
class CalidadCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        param = env['ir.config_parameter'].sudo()
        for clave, valor in (('retraso_min', 5), ('adelanto_min', 2), ('ancho_corredor_m', 150),
                             ('fuera_consecutivas', 3), ('gap_senal_min', 3), ('duracion_pct', 20)):
            param.set_param('transporte_calidad.' + clave, valor)
        param.set_param('transporte_gps.geocerca_modo', 'segmento')
        marca = env['fleet.vehicle.model.brand'].create({'name': 'TCAL'})
        modelo = env['fleet.vehicle.model'].create({'name': 'TCAL Bus', 'brand_id': marca.id})
        cls.bus1 = env['fleet.vehicle'].create({
            'model_id': modelo.id, 'license_plate': 'TCAL-001', 'capacidad_sentados': 30, 'capacidad_pie': 10,
            'traccar_device_id': 9901})
        cls.bus2 = env['fleet.vehicle'].create({
            'model_id': modelo.id, 'license_plate': 'TCAL-002', 'capacidad_sentados': 30, 'capacidad_pie': 10})
        cls.conductor = env['hr.employee'].create({
            'name': 'TCAL Conductor', 'es_conductor': True, 'licencia_nro': 'TCAL-LIC',
            'licencia_fecha_vencimiento': fields.Date.today() + timedelta(days=365)})
        paradas = {k: env['transporte.parada'].create({
            'name': 'TCAL P%s' % k, 'codigo': 'TCAL-P%s' % k, 'latitude': v[0], 'longitude': v[1],
            'radio_deteccion': v[2]}) for k, v in P.items()}
        cls.rutas = env['transporte.ruta']
        for codigo, secuencia in RUTAS.items():
            ruta = env['transporte.ruta'].create({
                'name': 'Ruta %s' % codigo, 'codigo': codigo, 'tiempo_estimado_min': secuencia[-1][1],
                'parada_ids': [(0, 0, {'parada_id': paradas[p].id, 'secuencia': i + 1, 'tiempo_desde_origen_min': t})
                               for i, (p, t) in enumerate(secuencia)]})
            ruta.action_sugerir_distancia()
            cls.rutas |= ruta
        cls.ruta1 = cls.rutas[0]
        cls.ayer = fields.Date.today() - timedelta(days=1)

    def _wizard(self, **kw):
        vals = {'fecha_inicio': self.ayer, 'dias': 1, 'ruta_ids': [(6, 0, self.rutas.ids)],
                'vehicle_ids': [(6, 0, (self.bus1 | self.bus2).ids)], 'driver_id': self.conductor.id}
        vals.update(kw)
        return self.env['transporte.calidad.simulacion'].create(vals)

    def _salida(self, hora=13, minuto=0):
        return datetime.combine(self.ayer, datetime.min.time()) + timedelta(hours=hora, minutes=minuto)

    def _viaje_manual(self, ruta=None, salida=None):
        """Viaje programado e iniciado (sin GPS) con la salida real = programada."""
        ruta = ruta or self.ruta1
        salida = salida or self._salida()
        viaje = self.env['transporte.viaje'].create({
            'ruta_id': ruta.id, 'vehicle_id': self.bus2.id, 'driver_id': self.conductor.id,
            'fecha_viaje': self.ayer, 'hora_salida_planificada': salida,
            'hora_llegada_planificada': salida + timedelta(minutes=ruta.tiempo_estimado_min)})
        viaje.action_programar()
        viaje.write({'state': 'in_progress', 'hora_salida_real': salida})
        return viaje

    def _llegadas(self, viaje, minutos):
        """Registra llegadas (minutos de retraso por parada; None = omitida) y finaliza el viaje."""
        for linea, retraso in zip(viaje.parada_line_ids.sorted('secuencia'), minutos):
            if retraso is None:
                linea.write({'estado_parada': 'omitida'})
            else:
                linea.write({'estado_parada': 'atendida', 'metodo_registro': 'manual',
                             'hora_llegada_real': linea.hora_planificada + timedelta(minutes=retraso)})
        ultima = viaje.parada_line_ids.sorted('secuencia')[-1]
        viaje.write({'state': 'completed', 'hora_llegada_real': ultima.hora_llegada_real or ultima.hora_planificada})
        viaje._evaluar_calidad()
        return viaje


class TestEvaluacion(CalidadCommon):

    def test_cp05_ejemplo_enunciado_retraso_8_min(self):
        """Parada programada 08:15 con tolerancia 5 min y llegada 08:23 => retraso de 8 min (incumple)."""
        salida = self._salida(13, 0)  # 08:00 Ecuador; la 3.ª parada (t=16) se ajusta a 08:15 abajo
        viaje = self._viaje_manual(salida=salida)
        linea = viaje.parada_line_ids.sorted('secuencia')[2]
        linea.write({'hora_planificada': salida + timedelta(minutes=15)})
        self._llegadas(viaje, [0, 0, 8, 0, 0, 0, 0])
        self.assertEqual(linea.retraso_min, 8.0)
        self.assertEqual(linea.puntualidad, 'atrasada')
        inc = viaje.incidencia_ids.filtered(lambda i: i.tipo == 'retraso_parada')
        self.assertEqual(len(inc), 1)
        self.assertEqual((inc.valor, inc.parada_id, inc.origen), (8.0, linea.parada_id, 'automatica'))
        self.assertEqual(viaje.resultado, 'incumple')
        self.assertFalse(viaje.puntual)
        self.assertTrue(viaje.cumple_ruta)

    def test_viaje_manual_perfecto_cumple_sin_reglas_gps(self):
        viaje = self._llegadas(self._viaje_manual(), [0, 1, 2, 0, 3, 5, 5])
        self.assertEqual(viaje.resultado, 'cumple')
        self.assertFalse(viaje.tiene_gps)
        self.assertFalse(viaje.incidencia_ids)
        self.assertEqual(viaje.porcentaje_paradas, 100.0)
        self.assertEqual(viaje.porcentaje_puntualidad, 100.0)
        self.assertEqual(viaje.retraso_llegada_min, 5.0)  # límite inclusivo

    def test_cp07_cp08_parada_omitida_e_incompleto(self):
        viaje = self._llegadas(self._viaje_manual(), [0, 0, None, 0, 0, None, None])
        self.assertEqual(set(viaje.incidencia_ids.mapped('tipo')), {'parada_omitida', 'recorrido_incompleto'})
        self.assertEqual(len(viaje.incidencia_ids.filtered(lambda i: i.tipo == 'parada_omitida')), 3)
        self.assertFalse(viaje.completo)
        self.assertAlmostEqual(viaje.porcentaje_paradas, 57.14, places=2)

    def test_cancelado_en_ruta_es_incompleto(self):
        viaje = self._viaje_manual()
        viaje.parada_line_ids.sorted('secuencia')[0].write({
            'estado_parada': 'atendida', 'hora_llegada_real': viaje.hora_salida_real})
        viaje.action_cancelar()
        self.assertEqual(viaje.resultado, 'incumple')
        self.assertIn('recorrido_incompleto', viaje.incidencia_ids.mapped('tipo'))

    def test_idempotencia_y_trazabilidad(self):
        """Reevaluar no duplica; una incidencia gestionada por un usuario no se borra."""
        viaje = self._llegadas(self._viaje_manual(), [0, 9, 0, 0, 0, 0, 0])
        for _i in range(3):
            viaje._evaluar_calidad()
        self.assertEqual(len(viaje.incidencia_ids), 1)
        inc = viaje.incidencia_ids
        inc.action_resolver()
        self.env['ir.config_parameter'].sudo().set_param('transporte_calidad.retraso_min', 10)
        viaje._evaluar_calidad()
        self.assertTrue(inc.exists(), 'una incidencia resuelta no debe desaparecer al reevaluar')
        self.assertEqual(viaje.resultado, 'cumple')

    def test_incidencia_abierta_obsoleta_se_elimina(self):
        viaje = self._llegadas(self._viaje_manual(), [0, 9, 0, 0, 0, 0, 0])
        self.env['ir.config_parameter'].sudo().set_param('transporte_calidad.retraso_min', 10)
        viaje._evaluar_calidad()
        self.assertFalse(viaje.incidencia_ids)

    def test_incidencia_automatica_no_se_borra_a_mano(self):
        viaje = self._llegadas(self._viaje_manual(), [0, 9, 0, 0, 0, 0, 0])
        with self.assertRaises(UserError):
            viaje.incidencia_ids.unlink()
        manual = self.env['transporte.incidencia'].create({'tipo': 'falla_mecanica', 'viaje_id': viaje.id})
        self.assertEqual((manual.vehicle_id, manual.ruta_id), (viaje.vehicle_id, viaje.ruta_id))
        self.assertTrue(manual.name.startswith('INC-'))
        manual.unlink()

    def test_borrador_limpia_evaluacion(self):
        viaje = self._viaje_manual()
        viaje.action_cancelar()
        viaje.action_borrador()
        self.assertEqual(viaje.resultado, 'sin_evaluar')
        self.assertFalse(viaje.incidencia_ids)

    def test_reevaluar_requiere_viaje_iniciado(self):
        viaje = self.env['transporte.viaje'].create({
            'ruta_id': self.ruta1.id, 'vehicle_id': self.bus2.id, 'driver_id': self.conductor.id,
            'hora_salida_planificada': self._salida(), 'hora_llegada_planificada': self._salida(14)})
        with self.assertRaises(UserError):
            viaje.action_reevaluar()

    def test_incidencias_esperadas_validas(self):
        viaje = self._viaje_manual()
        with self.assertRaises(ValidationError):
            viaje.incidencias_esperadas = 'retraso_parada, inventada'


class TestRutaYConfiguracion(CalidadCommon):

    def test_origen_destino_distancia(self):
        r = self.ruta1
        self.assertEqual(r.origen_parada_id.codigo, 'TCAL-P1')
        self.assertEqual(r.destino_parada_id.codigo, 'TCAL-P7')
        self.assertGreater(r.distancia_estimada_km, 3.0)
        with self.assertRaises(ValidationError):
            r.distancia_estimada_km = -1

    def test_trazado_referencia(self):
        self.assertEqual(len(self.ruta1._trazado_evaluacion()), 7)  # por defecto: paradas
        with self.assertRaises(ValidationError):
            self.ruta1.trazado_referencia = '[[1, 2]]'
        viaje = self._wizard().simular_viaje(self.ruta1, self.bus1, self._salida(11), 'puntual', 15)
        self.assertEqual(viaje.resultado, 'cumple')
        viaje.action_usar_como_trazado()
        self.assertGreater(self.ruta1.trazado_puntos, 7)
        self.assertIn(viaje.name, self.ruta1.trazado_origen)
        # el mismo recorrido evaluado contra su propio trazado no se desvía
        viaje._evaluar_calidad()
        self.assertFalse(viaje.desviado)
        self.ruta1.action_limpiar_trazado()
        self.assertEqual(self.ruta1.trazado_puntos, 0)

    def test_indicadores_por_ruta(self):
        self.assertEqual((self.ruta1.viajes_evaluados, self.ruta1.cumplimiento_pct), (0, 0.0))
        ok = self._llegadas(self._viaje_manual(salida=self._salida(9)), [0, 0, 0, 0, 0, 0, 0])
        mal = self._llegadas(self._viaje_manual(salida=self._salida(15)), [0, 9, None, 0, 0, None, None])
        self.assertTrue(ok.cumple_ruta)
        self.assertFalse(mal.cumple_ruta)
        vs = ok | mal
        self.assertEqual(self.ruta1.viajes_evaluados, 2)
        self.assertEqual(self.ruta1.cumplimiento_pct, 50.0)
        self.assertAlmostEqual(self.ruta1.puntualidad_pct,
                               100.0 * sum(vs.mapped('paradas_puntuales')) / sum(vs.mapped('paradas_atendidas')),
                               places=1)  # digits=(5, 1)
        self.assertEqual(self.rutas[1].viajes_evaluados, 0)

    def test_mapa_rutas(self):
        self.ruta1.ancho_corredor_m = 80
        datos = {r['codigo']: r for r in self.env['transporte.ruta'].get_mapa_rutas()}
        r1, r2 = datos['TCAL-R1'], datos['TCAL-R2']
        self.assertEqual([p['codigo'] for p in r1['paradas']], ['TCAL-P%s' % p for p, _t in RUTAS['TCAL-R1']])
        self.assertEqual(r1['trazado'], [[p['lat'], p['lon']] for p in r1['paradas']])  # sin trazado: paradas
        self.assertFalse(r1['trazado_real'])
        self.assertEqual((r1['corredor'], r2['corredor']), (80, 150.0))  # propio vs. global de Ajustes
        self.assertEqual((r1['evaluados'], r1['cumplimiento']), (0, 0.0))
        self.ruta1.trazado_referencia = '[[-1.2384, -78.6215], [-1.2500, -78.6300], [-1.2685, -78.6470]]'
        r1 = next(r for r in self.env['transporte.ruta'].get_mapa_rutas() if r['id'] == self.ruta1.id)
        self.assertTrue(r1['trazado_real'])
        self.assertEqual(len(r1['trazado']), 3)

    def test_settings_rechaza_tolerancias_negativas(self):
        with self.assertRaises(ValidationError):
            self.env['res.config.settings'].create({'cal_tol_retraso_min': -1})


class TestSimulacionYDeteccion(CalidadCommon):

    def test_cp13_plan_diez_recorridos_deteccion_correcta(self):
        """10 recorridos (3 rutas, 2 buses, mismo bus en varias rutas/horarios) => 100 % detección correcta."""
        accion = self._wizard().action_generar()
        viajes = self.env['transporte.viaje'].browse(accion['domain'][0][2])
        self.assertEqual(len(viajes), 10)
        self.assertTrue(all(viajes.mapped('simulado')))
        self.assertEqual(set(viajes.mapped('ruta_id')), set(self.rutas))
        self.assertGreaterEqual(len(set(viajes.filtered(lambda v: v.vehicle_id == self.bus1).mapped('ruta_id'))), 2)
        fallos = viajes.filtered(lambda v: v.deteccion_correcta != 'correcta')
        self.assertFalse(fallos, [(v.escenario_simulado, v.deteccion_detalle) for v in fallos])
        # cumplen: 3 puntuales + muestreo disperso + pérdida de señal (la pérdida de señal es una incidencia
        # de calidad de datos, no un incumplimiento del servicio: el bus visitó todas las paradas a tiempo)
        cumplen = viajes.filtered(lambda v: v.resultado == 'cumple')
        self.assertEqual(sorted(cumplen.mapped('escenario_simulado')),
                         ['muestreo_disperso', 'perdida_senal', 'puntual', 'puntual', 'puntual'])
        # las posiciones simuladas tienen ids negativos y nunca son la "última posición real" del bus
        posiciones = viajes.mapped('posicion_ids')
        self.assertTrue(all(p.simulado and p.traccar_position_id < 0 for p in posiciones))
        self.assertFalse(self.bus1.ultima_posicion_id)

    def test_cp12_geocerca_punto_vs_segmento(self):
        """Antes/después de la mejora PDCA con reportes cada 120 s."""
        param = self.env['ir.config_parameter'].sudo()
        wiz = self._wizard()
        param.set_param('transporte_gps.geocerca_modo', 'punto')
        antes = wiz.simular_viaje(self.ruta1, self.bus1, self._salida(7), 'muestreo_disperso', 120)
        param.set_param('transporte_gps.geocerca_modo', 'segmento')
        despues = wiz.simular_viaje(self.ruta1, self.bus1, self._salida(9), 'muestreo_disperso', 120)
        self.assertEqual(antes.deteccion_correcta, 'incorrecta')
        self.assertGreater(antes.paradas_omitidas, 0)
        self.assertEqual(despues.deteccion_correcta, 'correcta')
        self.assertEqual(despues.paradas_omitidas, 0)
        interp = despues.parada_line_ids.filtered(lambda l: 'interpolado' in (l.observaciones or ''))
        self.assertTrue(interp, 'al menos una parada debe detectarse por tramo interpolado')

    def test_wizard_valida_entradas(self):
        with self.assertRaises(UserError):
            self._wizard(ruta_ids=[(6, 0, self.ruta1.ids)]).action_generar()
        self.bus2.estado_operativo = 'mantenimiento'
        with self.assertRaises(UserError):
            self._wizard().action_generar()


class TestDashboard(CalidadCommon):

    def setUp(self):
        super().setUp()
        self.viajes = self.env['transporte.viaje'].browse(self._wizard().action_generar()['domain'][0][2])
        self.filtros = {'fecha_desde': fields.Date.to_string(self.ayer),
                        'fecha_hasta': fields.Date.to_string(self.ayer), 'datos': 'simulados'}

    def test_cp11_kpis_coinciden_con_registros(self):
        d = self.env['transporte.calidad.dashboard'].get_dashboard_data(
            dict(self.filtros, ruta_id=False, registrar=True))
        vs = self.env['transporte.viaje'].search([('fecha_viaje', '=', self.ayer), ('simulado', '=', True),
                                                  ('resultado', 'in', ('cumple', 'incumple'))])
        t = d['transporte']
        self.assertEqual(t['cumplimiento_rutas']['den'], len(vs))
        self.assertEqual(t['cumplimiento_rutas']['num'], len(vs.filtered('cumple_ruta')))
        self.assertEqual(t['paradas_cumplidas']['num'], sum(vs.mapped('paradas_atendidas')))
        self.assertEqual(t['paradas_cumplidas']['den'], sum(vs.mapped('total_paradas_viaje')))
        self.assertEqual(t['puntualidad_paradas']['num'], sum(vs.mapped('paradas_puntuales')))
        incs = self.env['transporte.incidencia'].search([('viaje_id', 'in', vs.ids), ('estado', '!=', 'descartada')])
        self.assertEqual(t['incidencias']['valor'], len(incs))
        self.assertEqual(sum(f['n'] for f in t['incidencias']['por_tipo']), len(incs))
        self.assertEqual(d['software']['deteccion_correcta']['valor'], 100.0)
        self.assertEqual(d['software']['integridad_gps']['valor'], 100.0)
        self.assertTrue(self.env['transporte.calidad.medicion'].search([('tipo', '=', 'dashboard')]))
        self.assertEqual(len(d['rutas']), len(self.env['transporte.ruta'].search([])))

    def test_dashboard_se_actualiza_con_nuevos_recorridos(self):
        antes = self.env['transporte.calidad.dashboard'].get_dashboard_data(self.filtros)
        self._wizard().simular_viaje(self.ruta1, self.bus1, self._salida(20), 'atrasado', 15)
        despues = self.env['transporte.calidad.dashboard'].get_dashboard_data(self.filtros)
        self.assertEqual(despues['resumen']['evaluados'], antes['resumen']['evaluados'] + 1)
        self.assertGreater(despues['transporte']['incidencias']['valor'], antes['transporte']['incidencias']['valor'])

    def test_filtro_reales_excluye_simulados(self):
        d = self.env['transporte.calidad.dashboard'].get_dashboard_data(dict(self.filtros, datos='reales'))
        self.assertEqual(d['resumen']['simulados'], 0)

    def test_rango_invalido(self):
        with self.assertRaises(UserError):
            self.env['transporte.calidad.dashboard'].get_dashboard_data(
                {'fecha_desde': '2026-11-20', 'fecha_hasta': '2026-11-01'})

    def test_exactitud_sync_con_traccar_simulado(self):
        """Exactitud = posiciones idénticas en Traccar y Odoo / verificadas."""
        ahora = fields.Datetime.now().replace(microsecond=0)
        parsed = [{'traccar_position_id': ID_BASE + i, 'traccar_device_id': 9901, 'latitud': -1.24 - i / 1e4,
                   'longitud': -78.62, 'velocidad_kmh': 18.52, 'fecha_gps': ahora - timedelta(minutes=4 - i),
                   'valida': True} for i in range(4)]
        self.env['transporte.gps.posicion'].registrar_posiciones(self.bus1, parsed)
        remotas = [{'id': p['traccar_position_id'], 'deviceId': 9901, 'latitude': p['latitud'],
                    'longitude': p['longitud'], 'speed': 10.0, 'valid': True,
                    'fixTime': p['fecha_gps'].strftime('%Y-%m-%dT%H:%M:%S.000+00:00')} for p in parsed[:3]]
        remotas[0]['latitude'] += 0.001  # 1 distinta, 1 faltante (la 4.ª)
        cliente = mock.Mock()
        cliente.get_positions.return_value = remotas
        res = self.env['transporte.calidad.dashboard'].verificar_exactitud_sync(client=cliente)
        self.assertEqual((res['verificadas'], res['iguales'], res['faltantes'], res['distintas']), (4, 2, 1, 1))
        self.assertEqual(res['valor'], 50.0)
        med = self.env['transporte.calidad.medicion'].search([('tipo', '=', 'exactitud_sync')], limit=1)
        self.assertEqual(med.valor, 50.0)
        self.assertFalse(med.ok)


class TestSeguridad(CalidadCommon):

    def test_usuario_consulta_solo_lee(self):
        usuario = new_test_user(self.env, login='tcal_consulta', groups='transporte_core.group_transporte_user')
        viaje = self._llegadas(self._viaje_manual(), [0, 9, 0, 0, 0, 0, 0])
        Inc = self.env['transporte.incidencia'].with_user(usuario)
        self.assertEqual(len(Inc.search([('viaje_id', '=', viaje.id)])), 1)
        with self.assertRaises(AccessError):
            Inc.create({'tipo': 'otro', 'viaje_id': viaje.id})
        # el dashboard es consultable por el rol de consulta
        d = self.env['transporte.calidad.dashboard'].with_user(usuario).get_dashboard_data({'registrar': True})
        self.assertIn('transporte', d)
        # y también el mapa de rutas con sus indicadores, sin poder modificar el trazado
        rutas = self.env['transporte.ruta'].with_user(usuario).get_mapa_rutas()
        r1 = next(r for r in rutas if r['id'] == self.ruta1.id)
        self.assertEqual(r1['evaluados'], 1)
        with self.assertRaises(AccessError):
            self.ruta1.with_user(usuario).write({'trazado_referencia': '[[0, 0], [1, 1]]'})

    def test_rpc_registro_gps_y_mediciones_restringido(self):
        """H-A03: métodos públicos que escriben con sudo() solo para gestor o procesos internos."""
        ahora = fields.Datetime.now().replace(microsecond=0)
        pos = {'traccar_position_id': ID_BASE + 900, 'traccar_device_id': 9901, 'latitud': -1.24,
               'longitud': -78.62, 'velocidad_kmh': 0.0, 'fecha_gps': ahora, 'valida': True}
        interno = new_test_user(self.env, login='tcal_interno', groups='base.group_user')
        consulta = new_test_user(self.env, login='tcal_consulta2', groups='transporte_core.group_transporte_user')
        portal = new_test_user(self.env, login='tcal_portal', groups='base.group_portal')
        for usuario in (interno, consulta, portal):
            with self.assertRaises(AccessError):
                self.env['transporte.gps.posicion'].with_user(usuario).registrar_posiciones(self.bus1, [pos])
            with self.assertRaises(AccessError):
                self.env['transporte.calidad.medicion'].with_user(usuario).registrar('dashboard', 5)
            with self.assertRaises(AccessError):
                self.env['fleet.vehicle'].with_user(usuario).procesar_webhook(dict(pos))
        self.assertFalse(self.env['transporte.gps.posicion'].search([('traccar_position_id', '=', ID_BASE + 900)]))
        gestor = new_test_user(self.env, login='tcal_gestor', groups='transporte_core.group_transporte_manager')
        res = self.env['transporte.gps.posicion'].with_user(gestor).registrar_posiciones(self.bus1, [pos])
        self.assertEqual(len(res['nuevas']), 1)
        self.assertTrue(self.env['transporte.calidad.medicion'].with_user(gestor).registrar('dashboard', 5))
        # proceso interno (sudo) desde un usuario sin permisos: el dashboard sigue registrando su tiempo
        d = self.env['transporte.calidad.dashboard'].with_user(consulta).get_dashboard_data({'registrar': True})
        self.assertIn('software', d)

    def test_simulacion_usa_hora_local_de_operacion(self):
        """H-A05: la zona del usuario no desplaza la hora planificada de los recorridos simulados."""
        self.env.user.tz = 'Europe/Brussels'
        asistente = self.env['transporte.calidad.simulacion'].new({})
        utc = asistente._a_utc(fields.Date.to_date('2026-11-21'), (6, 30))
        self.assertEqual(utc, datetime(2026, 11, 21, 11, 30))  # 06:30 America/Guayaquil = 11:30 UTC
