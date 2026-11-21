# -*- coding: utf-8 -*-
{
    'name': 'SGM-TB - Interfaz',
    'version': '16.0.1.0.0',
    'category': 'Operations/Transportation',
    'summary': 'Identidad visual de SGM-TB: pantalla de inicio, login, colores y navegación propios',
    'description': """
Interfaz de SGM-TB
==================
- Pantalla **En vivo** al estilo de las apps de transporte público: líneas con color, buses
  moviéndose en el mapa, recorrido tipo metro y llegadas estimadas con indicador de confianza.
- Pantalla de **Inicio** con indicadores en vivo (últimos 7 días), buses en ruta y accesos directos
  filtrados por los permisos del usuario.
- Página de **inicio de sesión** propia (sin marca de Odoo).
- Paleta, barra superior, formularios, listas y tarjetas con estilo propio.
- Título de la pestaña, favicon e icono de la aplicación propios; menú de usuario sin enlaces a odoo.com.
    """,
    'author': 'Equipo SGM-TB',
    'license': 'LGPL-3',
    'depends': ['transporte_calidad'],
    'data': [
        'views/inicio_views.xml',
        'views/en_vivo_views.xml',
        'views/webclient_templates.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            ('before', 'web/static/src/scss/primary_variables.scss',
             'transporte_ui/static/src/scss/primary_variables.scss'),
        ],
        'web.assets_backend': [
            'transporte_ui/static/src/scss/backend.scss',
            'transporte_ui/static/src/js/branding.js',
            'transporte_ui/static/src/js/inicio.js',
            'transporte_ui/static/src/xml/inicio.xml',
            'transporte_ui/static/src/scss/inicio.scss',
            'transporte_ui/static/src/js/en_vivo.js',
            'transporte_ui/static/src/xml/en_vivo.xml',
            'transporte_ui/static/src/scss/en_vivo.scss',
        ],
        'web.assets_frontend': [
            'transporte_ui/static/src/scss/login.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
