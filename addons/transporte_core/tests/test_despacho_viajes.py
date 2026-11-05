# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import fields
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError, UserError, AccessError


@tagged('post_install', '-at_install')
class TestTransporteDespachoViajes(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_user = cls.env.ref('transporte_core.group_transporte_user')
        cls.group_manager = cls.env.ref('transporte_core.group_transporte_manager')

        # Usuarios de prueba para RBAC
        cls.user_consulta = cls.env['res.users'].create({
            'name': 'Usuario Consulta Viajes',
            'login': 'user_viaje_consulta_test',
            'email': 'consulta_viajes@test.com',
            'groups_id': [(6, 0, [cls.group_user.id])]
        })

        cls.user_operador = cls.env['res.users'].create({
            'name': 'Administrador Operaciones Despacho',
            'login': 'admin_despacho_test',
            'email': 'admin_despacho@test.com',
            'groups_id': [(6, 0, [
                cls.group_manager.id,
                cls.env.ref('fleet.fleet_group_manager').id,
                cls.env.ref('hr.group_hr_user').id
            ])]
        })

        # Paradas base
        cls.parada_1 = cls.env['transporte.parada'].create({
            'name': 'Terminal Central',
            'codigo': 'PAR-DESP-01',
            'latitude': -1.241000,
            'longitude': -78.621000,
            'radio_deteccion': 35.0,
        })
        cls.parada_2 = cls.env['transporte.parada'].create({
            'name': 'Estación Universidad',
            'codigo': 'PAR-DESP-02',
            'latitude': -1.251000,
            'longitude': -78.631000,
            'radio_deteccion': 40.0,
        })
        cls.parada_3 = cls.env['transporte.parada'].create({
            'name': 'Terminal Sur',
            'codigo': 'PAR-DESP-03',
            'latitude': -1.261000,
            'longitude': -78.641000,
            'radio_deteccion': 30.0,
        })

        # Ruta con paradas
        cls.ruta_troncal = cls.env['transporte.ruta'].create({
            'name': 'Ruta 10 - Troncal Expresa',
            'codigo': 'RUT-DESP-10',
            'tipo_ruta': 'troncal',
            'tiempo_estimado_min': 40,
            'parada_ids': [
                (0, 0, {'parada_id': cls.parada_1.id, 'secuencia': 1, 'tiempo_desde_origen_min': 0}),
                (0, 0, {'parada_id': cls.parada_2.id, 'secuencia': 2, 'tiempo_desde_origen_min': 18}),
                (0, 0, {'parada_id': cls.parada_3.id, 'secuencia': 3, 'tiempo_desde_origen_min': 40}),
            ]
        })

        # Ruta vacía (sin paradas para validar rechazo)
        cls.ruta_vacia = cls.env['transporte.ruta'].create({
            'name': 'Ruta Vacía Sin Paradas',
            'codigo': 'RUT-DESP-VACIA',
            'tiempo_estimado_min': 15,
        })

        # Marca y modelo para flota
        cls.marca = cls.env['fleet.vehicle.model.brand'].create({'name': 'Volvo'})
        cls.modelo = cls.env['fleet.vehicle.model'].create({
            'name': 'B8R Padrón',
            'brand_id': cls.marca.id,
        })

        # Bus operativo disponible
        cls.bus_disponible = cls.env['fleet.vehicle'].create({
            'model_id': cls.modelo.id,
            'license_plate': 'BUS-DESP-01',
            'es_bus_pasajeros': True,
            'tipo_bus': 'padron',
            'capacidad_sentados': 35,
            'capacidad_pie': 25,
            'estado_operativo': 'disponible',
        })

        # Bus en mantenimiento
        cls.bus_taller = cls.env['fleet.vehicle'].create({
            'model_id': cls.modelo.id,
            'license_plate': 'BUS-DESP-TALLER',
            'es_bus_pasajeros': True,
            'tipo_bus': 'padron',
            'capacidad_sentados': 35,
            'capacidad_pie': 20,
            'estado_operativo': 'mantenimiento',
        })

        # Conductor habilitado con licencia vigente
        cls.conductor_habilitado = cls.env['hr.employee'].create({
            'name': 'Mario Caiza Conductor',
            'es_conductor': True,
            'licencia_nro': 'LIC-DESP-001',
            'licencia_categoria': 'tipo_d',
            'licencia_fecha_vencimiento': fields.Date.today() + timedelta(days=365),
        })

    def test_01_creacion_viaje_y_secuencia_codigo(self):
        """Verifica la creación del viaje en borrador y la generación del código con secuencia VJ/..."""
        ahora = fields.Datetime.now()
        llegada = ahora + timedelta(minutes=40)
        viaje = self.env['transporte.viaje'].create({
            'ruta_id': self.ruta_troncal.id,
            'vehicle_id': self.bus_disponible.id,
            'driver_id': self.conductor_habilitado.id,
            'fecha_viaje': fields.Date.today(),
            'hora_salida_planificada': ahora,
            'hora_llegada_planificada': llegada,
        })
        self.assertTrue(viaje.id)
        self.assertEqual(viaje.state, 'draft')
        self.assertTrue(viaje.name.startswith('VJ/'), f"El código de viaje '{viaje.name}' debe iniciar con 'VJ/'")

    def test_02_programacion_y_generacion_automatica_paradas(self):
        """Verifica que al programar el viaje se instancien automáticamente las paradas de la ruta con horarios calculados."""
        ahora = fields.Datetime.now()
        llegada = ahora + timedelta(minutes=40)
        viaje = self.env['transporte.viaje'].create({
            'ruta_id': self.ruta_troncal.id,
            'vehicle_id': self.bus_disponible.id,
            'driver_id': self.conductor_habilitado.id,
            'fecha_viaje': fields.Date.today(),
            'hora_salida_planificada': ahora,
            'hora_llegada_planificada': llegada,
        })
        viaje.action_programar()
        self.assertEqual(viaje.state, 'scheduled')
        self.assertEqual(len(viaje.parada_line_ids), 3, "El viaje debe haber generado 3 paradas.")

        # Verificar cálculo de horas planificadas por parada
        parada_1_line = viaje.parada_line_ids.filtered(lambda p: p.secuencia == 1)
        parada_2_line = viaje.parada_line_ids.filtered(lambda p: p.secuencia == 2)
        parada_3_line = viaje.parada_line_ids.filtered(lambda p: p.secuencia == 3)

        self.assertEqual(parada_1_line.hora_planificada, ahora)
        self.assertEqual(parada_2_line.hora_planificada, ahora + timedelta(minutes=18))
        self.assertEqual(parada_3_line.hora_planificada, ahora + timedelta(minutes=40))
        self.assertTrue(all(p.estado_parada == 'pendiente' for p in viaje.parada_line_ids))

    def test_03_rechazo_ruta_sin_paradas(self):
        """Comprueba que no se pueda programar un viaje sobre una ruta que no tiene paradas configuradas."""
        ahora = fields.Datetime.now()
        viaje = self.env['transporte.viaje'].create({
            'ruta_id': self.ruta_vacia.id,
            'vehicle_id': self.bus_disponible.id,
            'driver_id': self.conductor_habilitado.id,
            'fecha_viaje': fields.Date.today(),
            'hora_salida_planificada': ahora,
            'hora_llegada_planificada': ahora + timedelta(minutes=20),
        })
        with self.assertRaises(ValidationError):
            viaje.action_programar()

    def test_04_rechazo_bus_no_disponible(self):
        """Comprueba que no se pueda programar un viaje con un bus que esté en taller o no disponible."""
        ahora = fields.Datetime.now()
        viaje = self.env['transporte.viaje'].create({
            'ruta_id': self.ruta_troncal.id,
            'vehicle_id': self.bus_taller.id,  # Bus en taller
            'driver_id': self.conductor_habilitado.id,
            'fecha_viaje': fields.Date.today(),
            'hora_salida_planificada': ahora,
            'hora_llegada_planificada': ahora + timedelta(minutes=40),
        })
        with self.assertRaises(ValidationError):
            viaje.action_programar()

    def test_05_rechazo_conductor_licencia_vencida(self):
        """Comprueba que se impida programar un viaje si la licencia del conductor está vencida para la fecha."""
        conductor_vencido = self.env['hr.employee'].create({
            'name': 'Conductor Sin Vigencia',
            'es_conductor': False,  # Se crea primero como no conductor para eludir constrains de creación
        })
        conductor_vencido.write({
            'es_conductor': True,
            'licencia_nro': 'LIC-EXPIRED-99',
            'licencia_categoria': 'tipo_d',
            'licencia_fecha_vencimiento': fields.Date.today() + timedelta(days=5),
        })

        # Viaje programado para dentro de 10 días (cuando la licencia ya estará vencida)
        fecha_futura = fields.Date.today() + timedelta(days=10)
        salida_futura = fields.Datetime.now() + timedelta(days=10)
        viaje = self.env['transporte.viaje'].create({
            'ruta_id': self.ruta_troncal.id,
            'vehicle_id': self.bus_disponible.id,
            'driver_id': conductor_vencido.id,
            'fecha_viaje': fecha_futura,
            'hora_salida_planificada': salida_futura,
            'hora_llegada_planificada': salida_futura + timedelta(minutes=40),
        })
        with self.assertRaises(ValidationError):
            viaje.action_programar()

    def test_06_prevencion_conflictos_horarios_bus(self):
        """Verifica que se impida asignar el mismo bus a dos viajes en horarios superpuestos."""
        base_time = fields.Datetime.now() + timedelta(days=2)
        # Viaje 1: de 10:00 a 11:00
        viaje1 = self.env['transporte.viaje'].create({
            'ruta_id': self.ruta_troncal.id,
            'vehicle_id': self.bus_disponible.id,
            'driver_id': self.conductor_habilitado.id,
            'fecha_viaje': fields.Date.today() + timedelta(days=2),
            'hora_salida_planificada': base_time,
            'hora_llegada_planificada': base_time + timedelta(hours=1),
        })
        viaje1.action_programar()

        # Segundo conductor para probar conflicto de bus
        conductor_2 = self.env['hr.employee'].create({
            'name': 'Segundo Conductor',
            'es_conductor': True,
            'licencia_nro': 'LIC-DESP-002',
            'licencia_categoria': 'tipo_d',
            'licencia_fecha_vencimiento': fields.Date.today() + timedelta(days=365),
        })

        # Viaje 2: de 10:30 a 11:30 (se solapa en el bus)
        viaje2 = self.env['transporte.viaje'].create({
            'ruta_id': self.ruta_troncal.id,
            'vehicle_id': self.bus_disponible.id,  # Mismo bus
            'driver_id': conductor_2.id,
            'fecha_viaje': fields.Date.today() + timedelta(days=2),
            'hora_salida_planificada': base_time + timedelta(minutes=30),
            'hora_llegada_planificada': base_time + timedelta(minutes=90),
        })
        with self.assertRaises(ValidationError):
            viaje2.action_programar()

    def test_07_prevencion_conflictos_horarios_conductor(self):
        """Verifica que se impida asignar el mismo conductor a dos viajes en horarios superpuestos."""
        base_time = fields.Datetime.now() + timedelta(days=3)
        # Viaje 1
        viaje1 = self.env['transporte.viaje'].create({
            'ruta_id': self.ruta_troncal.id,
            'vehicle_id': self.bus_disponible.id,
            'driver_id': self.conductor_habilitado.id,
            'fecha_viaje': fields.Date.today() + timedelta(days=3),
            'hora_salida_planificada': base_time,
            'hora_llegada_planificada': base_time + timedelta(hours=1),
        })
        viaje1.action_programar()

        # Segundo bus disponible
        bus_2 = self.env['fleet.vehicle'].create({
            'model_id': self.modelo.id,
            'license_plate': 'BUS-DESP-02',
            'es_bus_pasajeros': True,
            'capacidad_sentados': 30,
            'capacidad_pie': 20,
            'estado_operativo': 'disponible',
        })

        # Viaje 2: Mismo conductor, horario solapado
        viaje2 = self.env['transporte.viaje'].create({
            'ruta_id': self.ruta_troncal.id,
            'vehicle_id': bus_2.id,
            'driver_id': self.conductor_habilitado.id,  # Mismo conductor
            'fecha_viaje': fields.Date.today() + timedelta(days=3),
            'hora_salida_planificada': base_time + timedelta(minutes=15),
            'hora_llegada_planificada': base_time + timedelta(minutes=75),
        })
        with self.assertRaises(ValidationError):
            viaje2.action_programar()

    def test_08_ciclo_completo_despacho_y_estados_bus(self):
        """Verifica el ciclo completo: Programar -> Iniciar -> Completar y actualización de estado de flota."""
        ahora = fields.Datetime.now()
        viaje = self.env['transporte.viaje'].create({
            'ruta_id': self.ruta_troncal.id,
            'vehicle_id': self.bus_disponible.id,
            'driver_id': self.conductor_habilitado.id,
            'fecha_viaje': fields.Date.today(),
            'hora_salida_planificada': ahora,
            'hora_llegada_planificada': ahora + timedelta(minutes=40),
        })
        # 1. Programar
        viaje.action_programar()
        self.assertEqual(viaje.state, 'scheduled')
        self.assertEqual(self.bus_disponible.estado_operativo, 'disponible')

        # 2. Iniciar (En ruta)
        viaje.action_iniciar()
        self.assertEqual(viaje.state, 'in_progress')
        self.assertTrue(viaje.hora_salida_real)
        self.assertEqual(self.bus_disponible.estado_operativo, 'en_servicio', "El bus debe pasar a 'en_servicio'.")

        # 3. Completar
        viaje.action_completar()
        self.assertEqual(viaje.state, 'completed')
        self.assertTrue(viaje.hora_llegada_real)
        self.assertEqual(self.bus_disponible.estado_operativo, 'disponible', "El bus debe liberarse a 'disponible'.")

    def test_09_registro_manual_llegada_paradas(self):
        """Verifica el registro manual de paradas durante un viaje en curso."""
        ahora = fields.Datetime.now()
        viaje = self.env['transporte.viaje'].create({
            'ruta_id': self.ruta_troncal.id,
            'vehicle_id': self.bus_disponible.id,
            'driver_id': self.conductor_habilitado.id,
            'fecha_viaje': fields.Date.today(),
            'hora_salida_planificada': ahora,
            'hora_llegada_planificada': ahora + timedelta(minutes=40),
        })
        viaje.action_programar()

        # Intentar registrar llegada antes de iniciar viaje -> Debe fallar
        parada_1_line = viaje.parada_line_ids.filtered(lambda p: p.secuencia == 1)
        with self.assertRaises(UserError):
            parada_1_line.action_registrar_llegada_manual()

        # Iniciar viaje
        viaje.action_iniciar()

        # Registrar parada 1
        parada_1_line.action_registrar_llegada_manual()
        self.assertEqual(parada_1_line.estado_parada, 'atendida')
        self.assertEqual(parada_1_line.metodo_registro, 'manual')
        self.assertTrue(parada_1_line.hora_llegada_real)

        # Intentar registrarla dos veces -> Debe fallar
        with self.assertRaises(UserError):
            parada_1_line.action_registrar_llegada_manual()

    def test_10_cancelacion_viaje_y_liberacion_bus(self):
        """Verifica que cancelar un viaje libere el bus y marque paradas pendientes como omitidas."""
        ahora = fields.Datetime.now()
        viaje = self.env['transporte.viaje'].create({
            'ruta_id': self.ruta_troncal.id,
            'vehicle_id': self.bus_disponible.id,
            'driver_id': self.conductor_habilitado.id,
            'fecha_viaje': fields.Date.today(),
            'hora_salida_planificada': ahora,
            'hora_llegada_planificada': ahora + timedelta(minutes=40),
        })
        viaje.action_programar()
        viaje.action_iniciar()
        self.assertEqual(self.bus_disponible.estado_operativo, 'en_servicio')

        viaje.action_cancelar()
        self.assertEqual(viaje.state, 'cancelled')
        self.assertEqual(self.bus_disponible.estado_operativo, 'disponible')
        self.assertTrue(all(p.estado_parada == 'omitida' for p in viaje.parada_line_ids))

    def test_11_permisos_rbac_viajes(self):
        """Verifica que el usuario de consulta solo lea y el administrador opere los viajes."""
        ahora = fields.Datetime.now()
        viaje = self.env['transporte.viaje'].create({
            'ruta_id': self.ruta_troncal.id,
            'vehicle_id': self.bus_disponible.id,
            'driver_id': self.conductor_habilitado.id,
            'fecha_viaje': fields.Date.today(),
            'hora_salida_planificada': ahora,
            'hora_llegada_planificada': ahora + timedelta(minutes=40),
        })

        # Usuario de consulta puede leer
        viaje_leido = self.env['transporte.viaje'].with_user(self.user_consulta).browse(viaje.id)
        self.assertEqual(viaje_leido.state, 'draft')

        # Usuario de consulta NO puede crear viajes
        with self.assertRaises(AccessError):
            self.env['transporte.viaje'].with_user(self.user_consulta).create({
                'ruta_id': self.ruta_troncal.id,
                'vehicle_id': self.bus_disponible.id,
                'driver_id': self.conductor_habilitado.id,
                'fecha_viaje': fields.Date.today(),
                'hora_salida_planificada': ahora,
                'hora_llegada_planificada': ahora + timedelta(minutes=40),
            })
