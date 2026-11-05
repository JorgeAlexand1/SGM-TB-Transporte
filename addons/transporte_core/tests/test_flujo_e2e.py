# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, time
from odoo import fields
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError, UserError


@tagged('post_install', '-at_install')
class TestTransporteFlujoE2E(TransactionCase):
    """
    Suite Integral E2E del Sistema de Gestión de Buses (Paso 1.4).
    Valida el ciclo de vida operativo completo (12 pasos) y 6 escenarios negativos.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Parada = cls.env['transporte.parada']
        cls.Ruta = cls.env['transporte.ruta']
        cls.RutaParada = cls.env['transporte.ruta.parada']
        cls.Vehicle = cls.env['fleet.vehicle']
        cls.Model = cls.env['fleet.vehicle.model']
        cls.Brand = cls.env['fleet.vehicle.model.brand']
        cls.Employee = cls.env['hr.employee']
        cls.Viaje = cls.env['transporte.viaje']
        cls.ViajeParada = cls.env['transporte.viaje.parada']

        cls.hoy = fields.Date.today()

        # Modelo y Marca de prueba
        cls.brand = cls.Brand.search([('name', '=', 'Mercedes')], limit=1)
        if not cls.brand:
            cls.brand = cls.Brand.create({'name': 'Mercedes'})

        cls.model = cls.Model.create({
            'name': 'Test Bus Urbano E2E',
            'brand_id': cls.brand.id,
        })

        # 1. Paradas E2E
        cls.parada_1 = cls.Parada.create({
            'name': 'E2E Parada 1 - Terminal',
            'codigo': 'E2E-PAR-01',
            'latitude': -1.240000,
            'longitude': -78.620000,
            'radio_deteccion': 35,
        })
        cls.parada_2 = cls.Parada.create({
            'name': 'E2E Parada 2 - Centro',
            'codigo': 'E2E-PAR-02',
            'latitude': -1.245000,
            'longitude': -78.625000,
            'radio_deteccion': 30,
        })
        cls.parada_3 = cls.Parada.create({
            'name': 'E2E Parada 3 - Hospital',
            'codigo': 'E2E-PAR-03',
            'latitude': -1.250000,
            'longitude': -78.630000,
            'radio_deteccion': 40,
        })
        cls.parada_4 = cls.Parada.create({
            'name': 'E2E Parada 4 - Terminal Sur',
            'codigo': 'E2E-PAR-04',
            'latitude': -1.255000,
            'longitude': -78.635000,
            'radio_deteccion': 35,
        })

        # 2. Ruta E2E
        cls.ruta_e2e = cls.Ruta.create({
            'name': 'E2E Ruta Troncal 01',
            'codigo': 'E2E-RUT-01',
            'tipo_ruta': 'urbana',
            'tiempo_estimado_min': 30,
        })
        cls.RutaParada.create({
            'ruta_id': cls.ruta_e2e.id,
            'parada_id': cls.parada_1.id,
            'secuencia': 1,
            'tiempo_desde_origen_min': 0,
        })
        cls.RutaParada.create({
            'ruta_id': cls.ruta_e2e.id,
            'parada_id': cls.parada_2.id,
            'secuencia': 2,
            'tiempo_desde_origen_min': 10,
        })
        cls.RutaParada.create({
            'ruta_id': cls.ruta_e2e.id,
            'parada_id': cls.parada_3.id,
            'secuencia': 3,
            'tiempo_desde_origen_min': 20,
        })
        cls.RutaParada.create({
            'ruta_id': cls.ruta_e2e.id,
            'parada_id': cls.parada_4.id,
            'secuencia': 4,
            'tiempo_desde_origen_min': 30,
        })

        # 3. Bus Disponible
        cls.bus_disponible = cls.Vehicle.create({
            'model_id': cls.model.id,
            'license_plate': 'E2E-BUS-01',
            'es_bus_pasajeros': True,
            'tipo_bus': 'padron',
            'capacidad_sentados': 30,
            'capacidad_pie': 20,
            'estado_operativo': 'disponible',
        })

        # 4. Bus en Mantenimiento (para pruebas negativas)
        cls.bus_mantenimiento = cls.Vehicle.create({
            'model_id': cls.model.id,
            'license_plate': 'E2E-BUS-MANT',
            'es_bus_pasajeros': True,
            'tipo_bus': 'padron',
            'capacidad_sentados': 30,
            'capacidad_pie': 20,
            'estado_operativo': 'mantenimiento',
        })

        # 5. Conductor Habilitado
        cls.conductor_habilitado = cls.Employee.create({
            'name': 'E2E Conductor Roberto Silva',
            'es_conductor': True,
            'licencia_nro': 'LIC-E2E-OK',
            'licencia_categoria': 'tipo_d',
            'licencia_fecha_vencimiento': cls.hoy + timedelta(days=365),
        })

    def test_01_flujo_integral_completo_12_pasos(self):
        """Validación del flujo operacional estándar desde la selección de ruta hasta el fin del viaje."""
        # Paso 1: Seleccionar ruta
        ruta = self.ruta_e2e
        self.assertTrue(ruta.exists())

        # Paso 2: Consultar sus paradas ordenadas
        paradas = ruta.parada_ids.sorted(key=lambda p: p.secuencia)
        self.assertEqual(len(paradas), 4)
        self.assertEqual(paradas[0].parada_id, self.parada_1)
        self.assertEqual(paradas[3].parada_id, self.parada_4)

        # Paso 3: Seleccionar bus disponible
        bus = self.bus_disponible
        self.assertEqual(bus.estado_operativo, 'disponible')
        self.assertTrue(bus.capacidad_total > 0)

        # Paso 4: Seleccionar conductor habilitado
        conductor = self.conductor_habilitado
        self.assertTrue(conductor.licencia_habilitada)

        # Paso 5: Crear viaje en borrador
        hora_salida = datetime.combine(self.hoy, time(8, 0, 0))
        hora_llegada = hora_salida + timedelta(minutes=30)
        viaje = self.Viaje.create({
            'ruta_id': ruta.id,
            'vehicle_id': bus.id,
            'driver_id': conductor.id,
            'fecha_viaje': self.hoy,
            'hora_salida_planificada': hora_salida,
            'hora_llegada_planificada': hora_llegada,
        })
        self.assertEqual(viaje.state, 'draft')
        self.assertEqual(len(viaje.parada_line_ids), 0)

        # Paso 6: Programar el viaje
        viaje.action_programar()
        self.assertEqual(viaje.state, 'scheduled')
        self.assertTrue(viaje.name.startswith('VJ/'))

        # Paso 7: Verificar generación automática de paradas
        self.assertEqual(len(viaje.parada_line_ids), 4)
        self.assertEqual(viaje.total_paradas_viaje, 4)
        self.assertEqual(viaje.paradas_atendidas, 0)

        # Paso 8: Comprobar horarios planificados de cada parada
        parada_items = viaje.parada_line_ids.sorted(key=lambda p: p.secuencia)
        self.assertEqual(parada_items[0].hora_planificada, hora_salida)
        self.assertEqual(parada_items[1].hora_planificada, hora_salida + timedelta(minutes=10))
        self.assertEqual(parada_items[2].hora_planificada, hora_salida + timedelta(minutes=20))
        self.assertEqual(parada_items[3].hora_planificada, hora_salida + timedelta(minutes=30))

        # Paso 9: Iniciar recorrido
        viaje.action_iniciar()
        self.assertEqual(viaje.state, 'in_progress')
        self.assertEqual(bus.estado_operativo, 'en_servicio')
        self.assertTrue(viaje.hora_salida_real)

        # Paso 10: Registrar manualmente las llegadas a las paradas
        parada_items[0].action_registrar_llegada_manual()
        self.assertEqual(parada_items[0].estado_parada, 'atendida')
        self.assertTrue(parada_items[0].hora_llegada_real)
        self.assertEqual(viaje.paradas_atendidas, 1)

        parada_items[1].action_registrar_llegada_manual()
        self.assertEqual(viaje.paradas_atendidas, 2)

        parada_items[2].action_registrar_llegada_manual()
        self.assertEqual(viaje.paradas_atendidas, 3)

        parada_items[3].action_registrar_llegada_manual()
        self.assertEqual(viaje.paradas_atendidas, 4)

        # Paso 11: Completar el viaje
        viaje.action_completar()
        self.assertEqual(viaje.state, 'completed')
        self.assertTrue(viaje.hora_llegada_real)

        # Paso 12: Comprobar estados finales del viaje y bus
        self.assertEqual(viaje.state, 'completed')
        self.assertEqual(bus.estado_operativo, 'disponible')

    def test_02_negativo_bus_no_disponible(self):
        """No se puede despachar un bus que se encuentra en mantenimiento."""
        hora_salida = datetime.combine(self.hoy, time(14, 0, 0))
        viaje = self.Viaje.create({
            'ruta_id': self.ruta_e2e.id,
            'vehicle_id': self.bus_mantenimiento.id,
            'driver_id': self.conductor_habilitado.id,
            'fecha_viaje': self.hoy,
            'hora_salida_planificada': hora_salida,
            'hora_llegada_planificada': hora_salida + timedelta(minutes=30),
        })
        with self.assertRaises(ValidationError):
            viaje.action_programar()

    def test_03_negativo_licencia_vencida_para_fecha_viaje(self):
        """Rechaza viajes cuando la fecha programada excede la vigencia de la licencia."""
        # Conductor cuya licencia vence en 5 días
        conductor_por_vencer = self.Employee.create({
            'name': 'E2E Conductor Licencia Corta',
            'es_conductor': True,
            'licencia_nro': 'LIC-E2E-CORTA',
            'licencia_categoria': 'tipo_c',
            'licencia_fecha_vencimiento': self.hoy + timedelta(days=5),
        })

        # Viaje creado en borrador para dentro de 10 días
        fecha_futura = self.hoy + timedelta(days=10)
        hora_salida = datetime.combine(fecha_futura, time(9, 0, 0))

        viaje = self.Viaje.create({
            'ruta_id': self.ruta_e2e.id,
            'vehicle_id': self.bus_disponible.id,
            'driver_id': conductor_por_vencer.id,
            'fecha_viaje': fecha_futura,
            'hora_salida_planificada': hora_salida,
            'hora_llegada_planificada': hora_salida + timedelta(minutes=30),
        })

        # Al intentar programar, debe rechazarlo porque la licencia estará vencida en esa fecha
        with self.assertRaises(ValidationError):
            viaje.action_programar()

    def test_04_negativo_horarios_superpuestos(self):
        """Impide programar dos viajes superpuestos para el mismo bus."""
        hora_1 = datetime.combine(self.hoy, time(10, 0, 0))
        hora_2 = datetime.combine(self.hoy, time(10, 45, 0))

        v1 = self.Viaje.create({
            'ruta_id': self.ruta_e2e.id,
            'vehicle_id': self.bus_disponible.id,
            'driver_id': self.conductor_habilitado.id,
            'fecha_viaje': self.hoy,
            'hora_salida_planificada': hora_1,
            'hora_llegada_planificada': hora_2,
        })
        v1.action_programar()

        # Otro conductor, pero el mismo bus en horario superpuesto (10:30 a 11:15)
        otro_conductor = self.Employee.create({
            'name': 'E2E Segundo Conductor',
            'es_conductor': True,
            'licencia_nro': 'LIC-E2E-OTRO',
            'licencia_categoria': 'tipo_d',
            'licencia_fecha_vencimiento': self.hoy + timedelta(days=300),
        })

        v2 = self.Viaje.create({
            'ruta_id': self.ruta_e2e.id,
            'vehicle_id': self.bus_disponible.id,
            'driver_id': otro_conductor.id,
            'fecha_viaje': self.hoy,
            'hora_salida_planificada': hora_1 + timedelta(minutes=30),
            'hora_llegada_planificada': hora_2 + timedelta(minutes=30),
        })

        with self.assertRaises(ValidationError):
            v2.action_programar()

    def test_05_negativo_registro_duplicado_parada(self):
        """Impide registrar dos veces la llegada a la misma parada."""
        hora_salida = datetime.combine(self.hoy, time(16, 0, 0))
        viaje = self.Viaje.create({
            'ruta_id': self.ruta_e2e.id,
            'vehicle_id': self.bus_disponible.id,
            'driver_id': self.conductor_habilitado.id,
            'fecha_viaje': self.hoy,
            'hora_salida_planificada': hora_salida,
            'hora_llegada_planificada': hora_salida + timedelta(minutes=30),
        })
        viaje.action_programar()
        viaje.action_iniciar()

        p1 = viaje.parada_line_ids.sorted(key=lambda p: p.secuencia)[0]
        p1.action_registrar_llegada_manual()
        self.assertEqual(p1.estado_parada, 'atendida')

        # Segundo intento de registro manual debe fallar
        with self.assertRaises(UserError):
            p1.action_registrar_llegada_manual()

    def test_06_negativo_transiciones_invalidas_y_preservacion_mantenimiento(self):
        """Verifica transiciones ilegales y la preservación de estado de mantenimiento del bus."""
        hora_salida = datetime.combine(self.hoy, time(18, 0, 0))
        viaje = self.Viaje.create({
            'ruta_id': self.ruta_e2e.id,
            'vehicle_id': self.bus_disponible.id,
            'driver_id': self.conductor_habilitado.id,
            'fecha_viaje': self.hoy,
            'hora_salida_planificada': hora_salida,
            'hora_llegada_planificada': hora_salida + timedelta(minutes=30),
        })

        # No se puede iniciar en borrador
        with self.assertRaises(UserError):
            viaje.action_iniciar()

        # No se puede completar en borrador
        with self.assertRaises(UserError):
            viaje.action_completar()

        viaje.action_programar()

        # No se puede completar en programado
        with self.assertRaises(UserError):
            viaje.action_completar()

        # Iniciar viaje
        viaje.action_iniciar()
        self.assertEqual(self.bus_disponible.estado_operativo, 'en_servicio')

        # Durante el viaje ocurre una avería y el bus es puesto en 'mantenimiento'
        self.bus_disponible.write({'estado_operativo': 'mantenimiento'})

        # Completar el viaje: el bus NO debe sobrescribirse a 'disponible'
        viaje.action_completar()
        self.assertEqual(viaje.state, 'completed')
        self.assertEqual(self.bus_disponible.estado_operativo, 'mantenimiento')

        # No se puede cancelar un viaje completado
        with self.assertRaises(UserError):
            viaje.action_cancelar()

        # No se puede eliminar un viaje completado
        with self.assertRaises(UserError):
            viaje.unlink()

        # Restaurar estado del bus para no afectar otros tests
        self.bus_disponible.write({'estado_operativo': 'disponible'})
