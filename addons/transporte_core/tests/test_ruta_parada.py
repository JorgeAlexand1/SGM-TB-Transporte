# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError, AccessError
from odoo.tools import mute_logger
from psycopg2 import IntegrityError


@tagged('post_install', '-at_install')
class TestTransporteRutaParada(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Grupos de seguridad
        cls.group_user = cls.env.ref('transporte_core.group_transporte_user')
        cls.group_manager = cls.env.ref('transporte_core.group_transporte_manager')

        # Usuarios de prueba para verificar permisos RBAC
        cls.user_consulta = cls.env['res.users'].create({
            'name': 'Usuario Consulta Transporte',
            'login': 'usuario_transporte_test',
            'email': 'consulta@transporte.test',
            'groups_id': [(6, 0, [cls.group_user.id])]
        })

        cls.user_operador = cls.env['res.users'].create({
            'name': 'Administrador Operaciones Transporte',
            'login': 'admin_transporte_test',
            'email': 'admin@transporte.test',
            'groups_id': [(6, 0, [cls.group_manager.id])]
        })

        # Paradas base de prueba
        cls.parada_norte = cls.env['transporte.parada'].create({
            'name': 'Terminal Norte',
            'codigo': 'PAR-TEST-001',
            'latitude': -1.240500,
            'longitude': -78.620100,
            'radio_deteccion': 35.0,
        })

        cls.parada_centro = cls.env['transporte.parada'].create({
            'name': 'Plaza Central',
            'codigo': 'PAR-TEST-002',
            'latitude': -1.250100,
            'longitude': -78.630200,
            'radio_deteccion': 40.0,
        })

        cls.parada_sur = cls.env['transporte.parada'].create({
            'name': 'Terminal Sur',
            'codigo': 'PAR-TEST-003',
            'latitude': -1.260800,
            'longitude': -78.640500,
            'radio_deteccion': 30.0,
        })

    def test_01_creacion_y_edicion_paradas(self):
        """Verifica la correcta creación y actualización de paradas."""
        parada = self.env['transporte.parada'].create({
            'name': 'Parada Parque Botánico',
            'codigo': 'PAR-TEST-004',
            'latitude': -1.245000,
            'longitude': -78.625000,
            'radio_deteccion': 25.0,
        })
        self.assertTrue(parada.id, "La parada debió crearse con un ID válido.")
        self.assertEqual(parada.name, 'Parada Parque Botánico')
        self.assertEqual(parada.codigo, 'PAR-TEST-004')
        self.assertTrue(parada.active)

        # Edición
        parada.write({
            'name': 'Parada Jardín Botánico',
            'radio_deteccion': 30.0
        })
        self.assertEqual(parada.name, 'Parada Jardín Botánico')
        self.assertEqual(parada.radio_deteccion, 30.0)

    def test_02_validacion_coordenadas(self):
        """Comprueba que no se permitan latitudes fuera de [-90, 90] ni longitudes fuera de [-180, 180]."""
        with self.assertRaises(ValidationError):
            self.env['transporte.parada'].create({
                'name': 'Parada Latitud Inválida',
                'codigo': 'PAR-ERR-LAT1',
                'latitude': 95.500000,
                'longitude': -78.620000,
            })

        with self.assertRaises(ValidationError):
            self.env['transporte.parada'].create({
                'name': 'Parada Latitud Negativa Inválida',
                'codigo': 'PAR-ERR-LAT2',
                'latitude': -91.000000,
                'longitude': -78.620000,
            })

        with self.assertRaises(ValidationError):
            self.env['transporte.parada'].create({
                'name': 'Parada Longitud Inválida',
                'codigo': 'PAR-ERR-LON1',
                'latitude': -1.250000,
                'longitude': 185.000000,
            })

        with self.assertRaises(ValidationError):
            self.env['transporte.parada'].create({
                'name': 'Parada Longitud Negativa Inválida',
                'codigo': 'PAR-ERR-LON2',
                'latitude': -1.250000,
                'longitude': -181.000000,
            })

    def test_03_validacion_radio_deteccion(self):
        """Comprueba que el radio de detección deba ser estrictamente positivo."""
        with self.assertRaises(ValidationError):
            self.env['transporte.parada'].create({
                'name': 'Parada Radio Cero',
                'codigo': 'PAR-ERR-RAD0',
                'latitude': -1.250000,
                'longitude': -78.620000,
                'radio_deteccion': 0.0,
            })

        with self.assertRaises(ValidationError):
            self.env['transporte.parada'].create({
                'name': 'Parada Radio Negativo',
                'codigo': 'PAR-ERR-RADNEG',
                'latitude': -1.250000,
                'longitude': -78.620000,
                'radio_deteccion': -15.0,
            })

    def test_04_codigo_duplicado_parada(self):
        """Comprueba la unicidad del código de parada."""
        with mute_logger('odoo.sql_db'):
            with self.assertRaises(IntegrityError):
                self.env['transporte.parada'].create({
                    'name': 'Parada Duplicada',
                    'codigo': 'PAR-TEST-001',  # Mismo código que parada_norte
                    'latitude': -1.270000,
                    'longitude': -78.630000,
                })

    def test_05_creacion_y_edicion_rutas_con_secuencia(self):
        """Verifica la creación de una ruta, asignación ordenada de paradas y cálculo de total_paradas."""
        ruta = self.env['transporte.ruta'].create({
            'name': 'Línea 01 - Troncal Norte-Sur',
            'codigo': 'RUT-TEST-001',
            'tipo_ruta': 'troncal',
            'tiempo_estimado_min': 45,
            'parada_ids': [
                (0, 0, {
                    'parada_id': self.parada_norte.id,
                    'secuencia': 1,
                    'tiempo_desde_origen_min': 0,
                }),
                (0, 0, {
                    'parada_id': self.parada_centro.id,
                    'secuencia': 2,
                    'tiempo_desde_origen_min': 20,
                }),
                (0, 0, {
                    'parada_id': self.parada_sur.id,
                    'secuencia': 3,
                    'tiempo_desde_origen_min': 45,
                }),
            ]
        })
        self.assertTrue(ruta.id)
        self.assertEqual(ruta.total_paradas, 3, "El total de paradas calculadas debe ser 3.")
        self.assertEqual(ruta.tipo_ruta, 'troncal')

        # Comprobar orden de paradas
        secuencias = ruta.parada_ids.mapped('secuencia')
        self.assertEqual(secuencias, [1, 2, 3], "Las paradas deben respetar el orden correlativo.")

    def test_06_codigo_duplicado_ruta(self):
        """Comprueba que no se puedan crear rutas con el mismo código."""
        self.env['transporte.ruta'].create({
            'name': 'Ruta Original',
            'codigo': 'RUT-TEST-UNIQUE',
            'tiempo_estimado_min': 30,
        })
        with mute_logger('odoo.sql_db'):
            with self.assertRaises(IntegrityError):
                self.env['transporte.ruta'].create({
                    'name': 'Ruta Copia',
                    'codigo': 'RUT-TEST-UNIQUE',
                    'tiempo_estimado_min': 35,
                })

    def test_07_secuencia_duplicada_misma_ruta(self):
        """Verifica que no se permita repetir el número de secuencia dentro de la misma ruta."""
        ruta = self.env['transporte.ruta'].create({
            'name': 'Ruta Secuencia Test',
            'codigo': 'RUT-TEST-SEC',
            'tiempo_estimado_min': 30,
        })
        self.env['transporte.ruta.parada'].create({
            'ruta_id': ruta.id,
            'parada_id': self.parada_norte.id,
            'secuencia': 1,
            'tiempo_desde_origen_min': 0,
        })
        with mute_logger('odoo.sql_db'):
            with self.assertRaises(IntegrityError):
                self.env['transporte.ruta.parada'].create({
                    'ruta_id': ruta.id,
                    'parada_id': self.parada_centro.id,
                    'secuencia': 1,  # Repite secuencia 1 en la misma ruta
                    'tiempo_desde_origen_min': 15,
                })

    def test_08_reutilizacion_paradas_entre_rutas(self):
        """Verifica que una misma parada física pueda pertenecer a múltiples rutas distintas."""
        ruta_a = self.env['transporte.ruta'].create({
            'name': 'Ruta A - Norte a Centro',
            'codigo': 'RUT-TEST-A',
            'tiempo_estimado_min': 20,
            'parada_ids': [
                (0, 0, {'parada_id': self.parada_norte.id, 'secuencia': 1, 'tiempo_desde_origen_min': 0}),
                (0, 0, {'parada_id': self.parada_centro.id, 'secuencia': 2, 'tiempo_desde_origen_min': 20}),
            ]
        })

        ruta_b = self.env['transporte.ruta'].create({
            'name': 'Ruta B - Sur a Centro',
            'codigo': 'RUT-TEST-B',
            'tiempo_estimado_min': 25,
            'parada_ids': [
                (0, 0, {'parada_id': self.parada_sur.id, 'secuencia': 1, 'tiempo_desde_origen_min': 0}),
                # Reutiliza parada_centro con secuencia 2 en otra ruta
                (0, 0, {'parada_id': self.parada_centro.id, 'secuencia': 2, 'tiempo_desde_origen_min': 25}),
            ]
        })

        self.assertTrue(ruta_a.id and ruta_b.id)
        self.assertIn(self.parada_centro, ruta_a.parada_ids.mapped('parada_id'))
        self.assertIn(self.parada_centro, ruta_b.parada_ids.mapped('parada_id'))

    def test_09_validacion_tiempos_negativos(self):
        """Comprueba que no se acepten tiempos negativos ni en la ruta ni en paradas intermedias."""
        with self.assertRaises(ValidationError):
            self.env['transporte.ruta'].create({
                'name': 'Ruta Tiempo Negativo',
                'codigo': 'RUT-ERR-TNEG',
                'tiempo_estimado_min': -15,
            })

        ruta = self.env['transporte.ruta'].create({
            'name': 'Ruta Base Válida',
            'codigo': 'RUT-VAL-001',
            'tiempo_estimado_min': 30,
        })

        with self.assertRaises(ValidationError):
            self.env['transporte.ruta.parada'].create({
                'ruta_id': ruta.id,
                'parada_id': self.parada_norte.id,
                'secuencia': 1,
                'tiempo_desde_origen_min': -5,
            })

    def test_10_permisos_acceso_rb_ac(self):
        """Comprueba que el usuario de consulta solo pueda leer y el administrador pueda crear/editar/eliminar."""
        # 1. Usuario de consulta puede leer
        paradas_leidas = self.env['transporte.parada'].with_user(self.user_consulta).search([])
        self.assertTrue(len(paradas_leidas) >= 3, "El usuario de consulta debe poder listar las paradas.")

        # 2. Usuario de consulta NO puede crear paradas
        with self.assertRaises(AccessError):
            self.env['transporte.parada'].with_user(self.user_consulta).create({
                'name': 'Parada No Autorizada',
                'codigo': 'PAR-UNAUTH-01',
                'latitude': -1.240000,
                'longitude': -78.620000,
            })

        # 3. Usuario de consulta NO puede crear rutas
        with self.assertRaises(AccessError):
            self.env['transporte.ruta'].with_user(self.user_consulta).create({
                'name': 'Ruta No Autorizada',
                'codigo': 'RUT-UNAUTH-01',
                'tiempo_estimado_min': 30,
            })

        # 4. Administrador de operaciones SÍ puede crear, editar y eliminar
        parada_admin = self.env['transporte.parada'].with_user(self.user_operador).create({
            'name': 'Parada Creada por Admin',
            'codigo': 'PAR-ADMIN-01',
            'latitude': -1.248000,
            'longitude': -78.628000,
            'radio_deteccion': 35.0,
        })
        self.assertTrue(parada_admin.id)

        parada_admin.with_user(self.user_operador).write({'name': 'Parada Modificada por Admin'})
        self.assertEqual(parada_admin.name, 'Parada Modificada por Admin')

        parada_admin.with_user(self.user_operador).unlink()
        self.assertFalse(parada_admin.exists())
