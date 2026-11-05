#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Carga Controlada e Idempotente de Datos de Demostración
Sistema de Gestión, Monitoreo y Calidad del Transporte en Buses (SGM-TB)

Base de datos objetivo: transporte_universitario_gc
Uso: Ejecutado dentro del contenedor odoo16_web o vía docker exec con odoo shell.
"""

import sys
import logging
from datetime import datetime, timedelta, time

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
_logger = logging.getLogger('cargar_datos_demo')

def cargar_datos_demo(env):
    _logger.info("=== Iniciando Carga Controlada de Datos DEMO SGM-TB ===")

    # 1. Paradas Georreferenciadas
    paradas_data = [
        {'codigo': 'DEMO-PAR-01', 'name': 'DEMO SGM-TB - Terminal Norte', 'latitude': -1.238400, 'longitude': -78.621500, 'radio_deteccion': 35},
        {'codigo': 'DEMO-PAR-02', 'name': 'DEMO SGM-TB - Parque Central', 'latitude': -1.242300, 'longitude': -78.625400, 'radio_deteccion': 30},
        {'codigo': 'DEMO-PAR-03', 'name': 'DEMO SGM-TB - Hospital Metropolitano', 'latitude': -1.247100, 'longitude': -78.629800, 'radio_deteccion': 40},
        {'codigo': 'DEMO-PAR-04', 'name': 'DEMO SGM-TB - Plaza Bolívar', 'latitude': -1.251500, 'longitude': -78.633200, 'radio_deteccion': 30},
        {'codigo': 'DEMO-PAR-05', 'name': 'DEMO SGM-TB - Centro Financiero', 'latitude': -1.256000, 'longitude': -78.637500, 'radio_deteccion': 35},
        {'codigo': 'DEMO-PAR-06', 'name': 'DEMO SGM-TB - Mercado Mayorista', 'latitude': -1.261200, 'longitude': -78.641000, 'radio_deteccion': 45},
        {'codigo': 'DEMO-PAR-07', 'name': 'DEMO SGM-TB - Terminal Sur', 'latitude': -1.268500, 'longitude': -78.647000, 'radio_deteccion': 50},
        {'codigo': 'DEMO-PAR-08', 'name': 'DEMO SGM-TB - Zona Industrial Este', 'latitude': -1.244000, 'longitude': -78.612000, 'radio_deteccion': 40},
        {'codigo': 'DEMO-PAR-09', 'name': 'DEMO SGM-TB - Intercambiador Este', 'latitude': -1.250500, 'longitude': -78.618500, 'radio_deteccion': 35},
        {'codigo': 'DEMO-PAR-10', 'name': 'DEMO SGM-TB - Complejo Polideportivo', 'latitude': -1.258000, 'longitude': -78.624000, 'radio_deteccion': 30},
        {'codigo': 'DEMO-PAR-11', 'name': 'DEMO SGM-TB - Av. Circunvalación Norte', 'latitude': -1.233000, 'longitude': -78.628000, 'radio_deteccion': 40},
        {'codigo': 'DEMO-PAR-12', 'name': 'DEMO SGM-TB - Portal de la Sierra', 'latitude': -1.272000, 'longitude': -78.652000, 'radio_deteccion': 50},
    ]

    Parada = env['transporte.parada']
    paradas_map = {}
    paradas_creadas = 0

    for p in paradas_data:
        existente = Parada.search([('codigo', '=', p['codigo'])], limit=1)
        if not existente:
            nueva = Parada.create(p)
            paradas_map[p['codigo']] = nueva
            paradas_creadas += 1
            _logger.info("Parada creada: [%s] %s", p['codigo'], p['name'])
        else:
            paradas_map[p['codigo']] = existente
            _logger.info("Parada ya existe: [%s] %s (omitida)", p['codigo'], p['name'])

    _logger.info("Paradas: %d creadas, %d existentes en catálogo.", paradas_creadas, len(paradas_map))

    # 2. Rutas con Secuencia de Paradas
    Ruta = env['transporte.ruta']
    RutaParada = env['transporte.ruta.parada']

    rutas_def = [
        {
            'codigo': 'DEMO-RUT-01',
            'name': 'DEMO SGM-TB - Línea 101 Troncal Norte-Sur',
            'tipo_ruta': 'troncal',
            'tiempo_estimado_min': 45,
            'descripcion': 'Eje troncal de transporte masivo conectando las terminales intermodales Norte y Sur.',
            'paradas': [
                ('DEMO-PAR-01', 1, 0),
                ('DEMO-PAR-02', 2, 8),
                ('DEMO-PAR-03', 3, 16),
                ('DEMO-PAR-04', 4, 23),
                ('DEMO-PAR-05', 5, 30),
                ('DEMO-PAR-06', 6, 38),
                ('DEMO-PAR-07', 7, 45),
            ]
        },
        {
            'codigo': 'DEMO-RUT-02',
            'name': 'DEMO SGM-TB - Línea 202 Transversal Este-Oeste',
            'tipo_ruta': 'urbana',
            'tiempo_estimado_min': 35,
            'descripcion': 'Línea de interconexión transversal este-sur articulando zonas industriales y centros de salud.',
            'paradas': [
                ('DEMO-PAR-08', 1, 0),
                ('DEMO-PAR-09', 2, 7),
                ('DEMO-PAR-03', 3, 15),
                ('DEMO-PAR-05', 4, 22),
                ('DEMO-PAR-10', 5, 29),
                ('DEMO-PAR-07', 6, 35),
            ]
        },
        {
            'codigo': 'DEMO-RUT-03',
            'name': 'DEMO SGM-TB - Línea 303 Expreso Periférico',
            'tipo_ruta': 'interurbana',
            'tiempo_estimado_min': 40,
            'descripcion': 'Servicio rápido perimetral con paradas estratégicas de alta demanda.',
            'paradas': [
                ('DEMO-PAR-11', 1, 0),
                ('DEMO-PAR-01', 2, 9),
                ('DEMO-PAR-09', 3, 20),
                ('DEMO-PAR-06', 4, 31),
                ('DEMO-PAR-12', 5, 40),
            ]
        },
    ]

    rutas_map = {}
    rutas_creadas = 0

    for r_data in rutas_def:
        existente = Ruta.search([('codigo', '=', r_data['codigo'])], limit=1)
        if not existente:
            ruta = Ruta.create({
                'codigo': r_data['codigo'],
                'name': r_data['name'],
                'tipo_ruta': r_data['tipo_ruta'],
                'tiempo_estimado_min': r_data['tiempo_estimado_min'],
                'descripcion': r_data['descripcion'],
            })
            for p_code, sec, t_min in r_data['paradas']:
                RutaParada.create({
                    'ruta_id': ruta.id,
                    'parada_id': paradas_map[p_code].id,
                    'secuencia': sec,
                    'tiempo_desde_origen_min': t_min,
                })
            rutas_map[r_data['codigo']] = ruta
            rutas_creadas += 1
            _logger.info("Ruta creada: [%s] %s con %d paradas.", r_data['codigo'], r_data['name'], len(r_data['paradas']))
        else:
            rutas_map[r_data['codigo']] = existente
            _logger.info("Ruta ya existe: [%s] %s (omitida)", r_data['codigo'], r_data['name'])

    _logger.info("Rutas: %d creadas, %d existentes en catálogo.", rutas_creadas, len(rutas_map))

    # 3. Flota de Buses (Modelos y Vehículos)
    FleetBrand = env['fleet.vehicle.model.brand']
    FleetModel = env['fleet.vehicle.model']
    FleetVehicle = env['fleet.vehicle']

    brand_mercedes = FleetBrand.search([('name', '=', 'Mercedes')], limit=1)
    if not brand_mercedes:
        brand_mercedes = FleetBrand.create({'name': 'Mercedes'})

    model_bus = FleetModel.search([('name', '=', 'DEMO SGM-TB - Chasis Bus Urbano')], limit=1)
    if not model_bus:
        model_bus = FleetModel.create({
            'name': 'DEMO SGM-TB - Chasis Bus Urbano',
            'brand_id': brand_mercedes.id,
        })

    buses_data = [
        {
            'license_plate': 'TB-DEMO-01',
            'model_id': model_bus.id,
            'es_bus_pasajeros': True,
            'tipo_bus': 'padron',
            'capacidad_sentados': 35,
            'capacidad_pie': 25,
            'estado_operativo': 'disponible',
        },
        {
            'license_plate': 'TB-DEMO-02',
            'model_id': model_bus.id,
            'es_bus_pasajeros': True,
            'tipo_bus': 'articulado',
            'capacidad_sentados': 50,
            'capacidad_pie': 70,
            'estado_operativo': 'disponible',
        },
        {
            'license_plate': 'TB-DEMO-03',
            'model_id': model_bus.id,
            'es_bus_pasajeros': True,
            'tipo_bus': 'microbus',
            'capacidad_sentados': 22,
            'capacidad_pie': 8,
            'estado_operativo': 'disponible',
        },
        {
            'license_plate': 'TB-DEMO-04',
            'model_id': model_bus.id,
            'es_bus_pasajeros': True,
            'tipo_bus': 'padron',
            'capacidad_sentados': 36,
            'capacidad_pie': 24,
            'estado_operativo': 'mantenimiento',
        },
    ]

    buses_map = {}
    buses_creados = 0

    for b in buses_data:
        existente = FleetVehicle.search([('license_plate', '=', b['license_plate'])], limit=1)
        if not existente:
            nuevo_bus = FleetVehicle.create(b)
            buses_map[b['license_plate']] = nuevo_bus
            buses_creados += 1
            _logger.info("Bus creado: Placa [%s], Tipo: %s, Capacidad: %d, Estado: %s",
                         b['license_plate'], b['tipo_bus'], nuevo_bus.capacidad_total, b['estado_operativo'])
        else:
            buses_map[b['license_plate']] = existente
            _logger.info("Bus ya existe: Placa [%s] (omitido)", b['license_plate'])

    _logger.info("Buses: %d creados, %d existentes en flota.", buses_creados, len(buses_map))

    # 4. Conductores Habilitados
    Employee = env['hr.employee']
    hoy = datetime.now().date()

    conductores_data = [
        {
            'name': 'DEMO SGM-TB - Carlos Silva',
            'es_conductor': True,
            'licencia_nro': 'LIC-DEMO-001',
            'licencia_categoria': 'tipo_d',
            'licencia_fecha_vencimiento': hoy + timedelta(days=730),
            'work_email': 'carlos.silva.demo@sgm-transporte.local',
        },
        {
            'name': 'DEMO SGM-TB - Manuel Paredes',
            'es_conductor': True,
            'licencia_nro': 'LIC-DEMO-002',
            'licencia_categoria': 'tipo_e',
            'licencia_fecha_vencimiento': hoy + timedelta(days=900),
            'work_email': 'manuel.paredes.demo@sgm-transporte.local',
        },
        {
            'name': 'DEMO SGM-TB - Andrea Morales',
            'es_conductor': True,
            'licencia_nro': 'LIC-DEMO-003',
            'licencia_categoria': 'tipo_c',
            'licencia_fecha_vencimiento': hoy + timedelta(days=365),
            'work_email': 'andrea.morales.demo@sgm-transporte.local',
        },
        {
            'name': 'DEMO SGM-TB - Personal Administrativo (No Conductor)',
            'es_conductor': False,
            'work_email': 'admin.apoyo.demo@sgm-transporte.local',
        },
    ]

    conductores_map = {}
    conductores_creados = 0

    for c in conductores_data:
        nombre_cond = c['name']
        existente = Employee.search([('name', '=', nombre_cond)], limit=1)
        if not existente:
            c_copy = dict(c)
            nuevo_c = Employee.create(c_copy)
            conductores_map[nombre_cond] = nuevo_c
            conductores_creados += 1
            _logger.info("Empleado/Conductor creado: '%s' (Conductor: %s, Habilitado: %s)",
                         nombre_cond, c.get('es_conductor'), nuevo_c.licencia_habilitada)
        else:
            conductores_map[nombre_cond] = existente
            _logger.info("Empleado/Conductor ya existe: '%s' (omitido)", nombre_cond)

    _logger.info("Conductores/Personal: %d creados, %d existentes.", conductores_creados, len(conductores_map))

    # 5. Viajes de Demostración
    Viaje = env['transporte.viaje']
    viajes_creados = 0

    # Viaje 1: Programado (Scheduled) listo para seguimiento operativo
    hora_base = datetime.combine(hoy, time(7, 30, 0))
    viaje_1_existente = Viaje.search([
        ('ruta_id', '=', rutas_map['DEMO-RUT-01'].id),
        ('vehicle_id', '=', buses_map['TB-DEMO-01'].id),
        ('fecha_viaje', '=', hoy),
        ('hora_salida_planificada', '=', hora_base),
    ], limit=1)

    if not viaje_1_existente:
        v1 = Viaje.create({
            'ruta_id': rutas_map['DEMO-RUT-01'].id,
            'vehicle_id': buses_map['TB-DEMO-01'].id,
            'driver_id': conductores_map['DEMO SGM-TB - Carlos Silva'].id,
            'fecha_viaje': hoy,
            'hora_salida_planificada': hora_base,
            'hora_llegada_planificada': hora_base + timedelta(minutes=45),
            'notas': 'DEMO SGM-TB - Despacho matutino troncal Norte-Sur.',
        })
        v1.action_programar()
        viajes_creados += 1
        _logger.info("Viaje 1 creado y PROGRAMADO: '%s' con %d paradas snapshot.", v1.name, v1.total_paradas_viaje)
    else:
        _logger.info("Viaje 1 ya existe: '%s' (omitido)", viaje_1_existente.name)

    # Viaje 2: Borrador (Draft) para demostración interactiva
    hora_base_2 = datetime.combine(hoy, time(10, 0, 0))
    viaje_2_existente = Viaje.search([
        ('ruta_id', '=', rutas_map['DEMO-RUT-02'].id),
        ('vehicle_id', '=', buses_map['TB-DEMO-02'].id),
        ('fecha_viaje', '=', hoy),
        ('hora_salida_planificada', '=', hora_base_2),
    ], limit=1)

    if not viaje_2_existente:
        v2 = Viaje.create({
            'ruta_id': rutas_map['DEMO-RUT-02'].id,
            'vehicle_id': buses_map['TB-DEMO-02'].id,
            'driver_id': conductores_map['DEMO SGM-TB - Manuel Paredes'].id,
            'fecha_viaje': hoy,
            'hora_salida_planificada': hora_base_2,
            'hora_llegada_planificada': hora_base_2 + timedelta(minutes=35),
            'notas': 'DEMO SGM-TB - Despacho programado transversal en borrador.',
        })
        viajes_creados += 1
        _logger.info("Viaje 2 creado en BORRADOR: '%s'.", v2.name)
    else:
        _logger.info("Viaje 2 ya existe: '%s' (omitido)", viaje_2_existente.name)

    # Confirmar transacción
    env.cr.commit()
    _logger.info("=== Carga DEMO SGM-TB finalizada exitosamente ===")
    return {
        'paradas': len(paradas_map),
        'rutas': len(rutas_map),
        'buses': len(buses_map),
        'conductores': len(conductores_map),
        'viajes_creados': viajes_creados
    }

if __name__ == '__main__':
    # Si se invoca fuera de un entorno Odoo directo, importar módulos de Odoo
    try:
        import odoo
        from odoo.tools import config
        db_name = os.environ.get('ODOO_DB_NAME', 'transporte_universitario_gc')
        db_user = os.environ.get('POSTGRES_USER', 'odoo')
        db_password = os.environ.get('POSTGRES_PASSWORD', 'odoo_secret_pwd')
        config.parse_config([
            '-c', '/etc/odoo/odoo.conf',
            '-d', db_name,
            '--db_host=db',
            f'--db_user={db_user}',
            f'--db_password={db_password}'
        ])
        registry = odoo.registry(db_name)
        with registry.cursor() as cr:
            env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
            res = cargar_datos_demo(env)
            print("Resultado:", res)
    except Exception as e:
        _logger.exception("Error cargando datos de demostración: %s", e)
        sys.exit(1)
