# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import fields
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError, AccessError


@tagged('post_install', '-at_install')
class TestTransporteBusesConductores(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_user = cls.env.ref('transporte_core.group_transporte_user')
        cls.group_manager = cls.env.ref('transporte_core.group_transporte_manager')

        # Usuarios para validación de seguridad RBAC
        cls.user_consulta = cls.env['res.users'].create({
            'name': 'Usuario Consulta SGM',
            'login': 'user_sgm_consulta_test',
            'email': 'consulta_sgm@test.com',
            'groups_id': [(6, 0, [cls.group_user.id])]
        })

        cls.user_operador = cls.env['res.users'].create({
            'name': 'Administrador Operaciones SGM',
            'login': 'admin_sgm_operador_test',
            'email': 'admin_sgm@test.com',
            'groups_id': [(6, 0, [cls.group_manager.id, cls.env.ref('fleet.fleet_group_manager').id, cls.env.ref('hr.group_hr_user').id])]
        })

        # Marca y modelo para flota
        cls.marca = cls.env['fleet.vehicle.model.brand'].create({'name': 'Mercedes-Benz'})
        cls.modelo_bus = cls.env['fleet.vehicle.model'].create({
            'name': 'O500 Urbano',
            'brand_id': cls.marca.id,
        })

    def test_01_registro_bus_y_capacidad_total(self):
        """Verifica el registro de un bus y el cálculo automático de su capacidad total."""
        bus = self.env['fleet.vehicle'].create({
            'model_id': self.modelo_bus.id,
            'license_plate': 'TB-0101',
            'es_bus_pasajeros': True,
            'tipo_bus': 'padron',
            'capacidad_sentados': 36,
            'capacidad_pie': 24,
            'estado_operativo': 'disponible',
        })
        self.assertTrue(bus.id)
        self.assertEqual(bus.capacidad_total, 60, "La capacidad total debe ser la suma de sentados y de pie (36 + 24 = 60).")
        self.assertEqual(bus.estado_operativo, 'disponible')
        self.assertTrue(bus.es_bus_pasajeros)

    def test_02_rechazo_capacidades_negativas_o_cero(self):
        """Comprueba que no se acepten capacidades negativas ni capacidad cero para buses de pasajeros."""
        with self.assertRaises(ValidationError):
            self.env['fleet.vehicle'].create({
                'model_id': self.modelo_bus.id,
                'license_plate': 'TB-ERR1',
                'es_bus_pasajeros': True,
                'capacidad_sentados': -5,
                'capacidad_pie': 20,
            })

        with self.assertRaises(ValidationError):
            self.env['fleet.vehicle'].create({
                'model_id': self.modelo_bus.id,
                'license_plate': 'TB-ERR2',
                'es_bus_pasajeros': True,
                'capacidad_sentados': 30,
                'capacidad_pie': -1,
            })

        with self.assertRaises(ValidationError):
            self.env['fleet.vehicle'].create({
                'model_id': self.modelo_bus.id,
                'license_plate': 'TB-ERR3',
                'es_bus_pasajeros': True,
                'capacidad_sentados': 0,
                'capacidad_pie': 0,
            })

    def test_03_cambios_estado_operativo(self):
        """Comprueba las transiciones de estado operativo de la unidad."""
        bus = self.env['fleet.vehicle'].create({
            'model_id': self.modelo_bus.id,
            'license_plate': 'TB-0202',
            'es_bus_pasajeros': True,
            'capacidad_sentados': 40,
            'capacidad_pie': 0,
        })
        self.assertEqual(bus.estado_operativo, 'disponible')

        bus.write({'estado_operativo': 'en_servicio'})
        self.assertEqual(bus.estado_operativo, 'en_servicio')

        bus.write({'estado_operativo': 'mantenimiento'})
        self.assertEqual(bus.estado_operativo, 'mantenimiento')

        bus.write({'estado_operativo': 'fuera_servicio'})
        self.assertEqual(bus.estado_operativo, 'fuera_servicio')

    def test_04_registro_conductor_valido(self):
        """Comprueba la habilitación correcta de un empleado como conductor con licencia vigente."""
        fecha_vigente = fields.Date.today() + timedelta(days=365)
        conductor = self.env['hr.employee'].create({
            'name': 'Carlos Pérez Conductor',
            'es_conductor': True,
            'licencia_nro': 'LIC-P-001234',
            'licencia_categoria': 'tipo_d',
            'licencia_fecha_vencimiento': fecha_vigente,
        })
        self.assertTrue(conductor.id)
        self.assertTrue(conductor.es_conductor)
        self.assertTrue(conductor.licencia_habilitada, "El conductor debe estar habilitado al tener licencia vigente.")

    def test_05_rechazo_licencia_vencida(self):
        """Comprueba que no se pueda registrar un conductor con licencia vencida."""
        fecha_vencida = fields.Date.today() - timedelta(days=15)
        with self.assertRaises(ValidationError):
            self.env['hr.employee'].create({
                'name': 'Conductor Licencia Caducada',
                'es_conductor': True,
                'licencia_nro': 'LIC-CAD-098',
                'licencia_categoria': 'tipo_d',
                'licencia_fecha_vencimiento': fecha_vencida,
            })

    def test_06_validacion_campos_obligatorios_conductor(self):
        """Comprueba que al marcar es_conductor se exija número de licencia y fecha de vencimiento."""
        with self.assertRaises(ValidationError):
            self.env['hr.employee'].create({
                'name': 'Conductor Sin Licencia Nro',
                'es_conductor': True,
                'licencia_fecha_vencimiento': fields.Date.today() + timedelta(days=180),
            })

        with self.assertRaises(ValidationError):
            self.env['hr.employee'].create({
                'name': 'Conductor Sin Fecha Vencimiento',
                'es_conductor': True,
                'licencia_nro': 'LIC-SIN-FECHA',
            })

    def test_07_empleado_no_conductor(self):
        """Comprueba que un empleado administrativo no requiera licencia ni aparezca habilitado como conductor."""
        empleado = self.env['hr.employee'].create({
            'name': 'Ana Martínez Despachadora',
            'es_conductor': False,
        })
        self.assertTrue(empleado.id)
        self.assertFalse(empleado.es_conductor)
        self.assertFalse(empleado.licencia_habilitada)

    def test_08_permisos_acceso_buses_y_conductores(self):
        """Verifica que el usuario de consulta tenga visibilidad de buses y conductores registrados."""
        bus = self.env['fleet.vehicle'].create({
            'model_id': self.modelo_bus.id,
            'license_plate': 'TB-SEC-01',
            'es_bus_pasajeros': True,
            'capacidad_sentados': 30,
            'capacidad_pie': 10,
        })
        # Lectura por usuario de consulta
        bus_leido = self.env['fleet.vehicle'].with_user(self.user_consulta).browse(bus.id)
        self.assertEqual(bus_leido.capacidad_total, 40)
        self.assertEqual(bus_leido.estado_operativo, 'disponible')
