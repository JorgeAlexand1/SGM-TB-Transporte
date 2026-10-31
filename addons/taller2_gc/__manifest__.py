{
    'name': 'TechStore Quality - Taller Realista con Fallas',
    'version': '1.6',
    'summary': 'Clientes, productos, ventas y API de TechStore',
    'description': 'Gestión de clientes, productos y ventas con métricas de calidad.',
    'author': 'Taller ACS',
    'category': 'Education',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'data/techstore_demo_data.xml',
        'views/techstore_cliente_views.xml',
        'views/techstore_producto_views.xml',
        'views/techstore_venta_views.xml',
        'views/z_techstore_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'taller2_gc/static/src/js/input_validation.js',
        ],
    },
    'installable': True,
    'application': True,
}
