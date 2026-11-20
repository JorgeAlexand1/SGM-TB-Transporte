# -*- coding: utf-8 -*-
{
    'name': 'Transporte en Buses - Telemetría GPS (Traccar)',
    'version': '16.0.1.0.0',
    'category': 'Operations/Transportation',
    'summary': 'Integración Odoo-Traccar: posiciones GPS, geocercas de paradas, señal y mapa',
    'description': """
Integración con Traccar Server (SGM-TB, actividades A3 y A5)
============================================================
- Vincula un dispositivo Traccar con cada bus (fleet.vehicle).
- Sincronización incremental por cron (API REST) y por webhook (forward), sin duplicados
  (restricción UNIQUE sobre el id de posición de Traccar).
- Asocia posiciones al viaje en curso, calcula distancia/velocidad y registra automáticamente
  la llegada a paradas por geocerca (Haversine).
- Detección de señal GPS desactualizada ("sin señal").
- Log de sincronización y mapa Leaflet/OpenStreetMap.
    """,
    'author': 'Equipo SGM-TB',
    'license': 'LGPL-3',
    'depends': ['transporte_core'],
    'external_dependencies': {'python': ['requests']},
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/fleet_vehicle_views.xml',
        'views/gps_posicion_views.xml',
        'views/gps_sync_log_views.xml',
        'views/transporte_viaje_views.xml',
        'views/res_config_settings_views.xml',
        'views/gps_map_action.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'transporte_gps_traccar/static/src/js/gps_map.js',
            'transporte_gps_traccar/static/src/xml/gps_map.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
