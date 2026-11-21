# -*- coding: utf-8 -*-
{
    'name': 'Transporte en Buses - Calidad del Servicio, Incidencias y KPIs',
    'version': '16.0.1.0.0',
    'category': 'Operations/Transportation',
    'summary': 'Detección automática de incumplimientos, métricas de transporte y de calidad del software, dashboard',
    'description': """
Calidad del servicio de transporte universitario (SGM-TB, actividades A5-A8)
============================================================================
- Evaluación automática de cada recorrido: retrasos por parada, de salida y de llegada,
  paradas omitidas, recorridos incompletos, diferencia de tiempos, desviación del corredor
  de la ruta y pérdida de señal GPS, con tolerancias configurables.
- Registro de incidencias automáticas (idempotente) y manuales.
- Indicadores de transporte (8) y de calidad del software (4) calculados en vivo desde la BD.
- Dashboard en Odoo (OWL + Chart.js + Leaflet), vistas pivot/gráfico e informe PDF por viaje.
- Mapa de rutas con el trazado usado para detectar desvíos e indicadores de cumplimiento por ruta.
- Generador de recorridos SIMULADOS (identificados como tales) para escenarios de incumplimiento.
    """,
    'author': 'Equipo SGM-TB',
    'license': 'LGPL-3',
    'depends': ['transporte_core', 'transporte_gps_traccar'],
    'data': [
        'security/ir.model.access.csv',
        'data/transporte_calidad_data.xml',
        'data/ir_cron.xml',
        'report/informe_viaje.xml',
        'views/transporte_incidencia_views.xml',
        'views/transporte_viaje_views.xml',
        'views/transporte_ruta_views.xml',
        'views/transporte_calidad_medicion_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/simulacion_views.xml',
        'views/dashboard_action.xml',
        'views/mapa_rutas_action.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'transporte_calidad/static/src/js/dashboard.js',
            'transporte_calidad/static/src/xml/dashboard.xml',
            'transporte_calidad/static/src/scss/dashboard.scss',
            'transporte_calidad/static/src/js/mapa_rutas.js',
            'transporte_calidad/static/src/xml/mapa_rutas.xml',
            'transporte_calidad/static/src/scss/mapa_rutas.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
