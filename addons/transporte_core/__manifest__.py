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
- Extensión de unidades de flota (buses) sobre fleet.vehicle.
- Extensión de perfiles de conductores sobre hr.employee.
- Catálogo maestro de paradas georreferenciadas y secuencias de ruta.
- Planificación de horarios y frecuencias.
- Despacho y ejecución operativa manual de viajes.

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
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
