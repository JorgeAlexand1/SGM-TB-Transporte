# Transporte Core - Núcleo Operativo del Sistema de Buses (SGM-TB)

## Descripción General
`transporte_core` es el módulo base del **Sistema de Gestión, Monitoreo y Evaluación de la Calidad del Transporte en Buses (SGM-TB)** sobre Odoo 16.0 Community.

Este módulo define la capa de dominio principal para:
- La flota de buses (extensión de `fleet.vehicle`).
- El equipo de conductores (extensión de `hr.employee`).
- El catálogo de paradas georreferenciadas (`transporte.parada`).
- La definición de rutas y secuencias de paradas (`transporte.ruta` y `transporte.ruta.parada`).
- La programación de horarios (`transporte.horario`).
- La ejecución operativa y manual de viajes (`transporte.viaje` y `transporte.viaje.parada`).

## Principios Arquitectónicos
1. **Desacoplamiento Estricto**: No posee dependencias hacia módulos de telemetría GPS (`transporte_gps_traccar`) ni de calidad (`transporte_calidad`).
2. **Operación Manual Autónoma**: Permite despachar viajes y registrar el avance en las paradas de forma manual en la interfaz web de Odoo, garantizando la continuidad operativa ante contingencias.
3. **Extensibilidad**: Los módulos posteriores de GPS y Calidad extenderán las entidades de este módulo mediante el mecanismo de herencia `_inherit`.

## Estructura de Directorios
```text
addons/transporte_core/
├── __init__.py                 # Inicializador del paquete Python
├── __manifest__.py             # Manifiesto oficial del módulo Odoo
├── models/                     # Modelos de datos Odoo
│   └── __init__.py
├── security/                   # Reglas de seguridad y accesos
│   └── ir.model.access.csv     # Matriz de permisos de lectura/escritura/creación/eliminación
├── views/                      # Definiciones de vistas XML (formularios, árboles, kanban)
├── data/                       # Datos maestros y demostrativos
└── README.md                   # Documentación técnica del módulo
```

## Dependencias
- `base`: Core de Odoo 16.
- `fleet`: Gestión oficial de flota de vehículos.
- `hr`: Gestión oficial de empleados y conductores.
- `mail`: Mensajería, chatter y trazabilidad de cambios de estado.
