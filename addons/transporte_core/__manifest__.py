# -*- coding: utf-8 -*-
{
    'name': 'Gestión de Transporte en Buses - Núcleo Operativo',
    'version': '16.0.1.0.0',
    'category': 'Operations/Transportation',
    'summary': 'Gestión central de flota de buses, conductores, rutas, paradas, horarios y viajes',
    'description': """
Módulo Núcleo del Sistema de Gestión y Monitoreo del Transporte en Buses (SGM-TB)
================================================================================
Este módulo constituye la capa base operativa del sistema de transporte,
proporcionando los cimientos para:
- Catálogo maestro de paradas georreferenciadas con radio de detección.
- Definición de rutas y secuencias ordenadas de paradas con tiempos de viaje.
- Extensión de unidades de flota (buses) sobre fleet.vehicle (capacidades, tipo, estado operativo).
- Extensión de perfiles de conductores sobre hr.employee (licencias, vigencia, habilitación).
- Despacho y ejecución operativa manual de viajes (Paso 1.3).

Diseñado con arquitectura desacoplada, sin dependencias hacia telemetría GPS ni calidad.
    """,
    'author': 'Equipo SGM-TB',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'fleet',
        'hr',
        'mail',
    ],
    'data': [
        'security/transporte_security.xml',
        'security/ir.model.access.csv',
        'data/transporte_sequence.xml',
        'views/transporte_parada_views.xml',
        'views/transporte_ruta_views.xml',
        'views/fleet_vehicle_views.xml',
        'views/hr_employee_views.xml',
        'views/transporte_viaje_views.xml',
        'views/transporte_menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
