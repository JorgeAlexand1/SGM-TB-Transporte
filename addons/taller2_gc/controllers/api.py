from odoo import http
from odoo.http import request
import json
from odoo.exceptions import ValidationError


class TechStoreAPI(http.Controller):

    # =========================================================
    # FUNCIÓN PARA LEER JSON DEL BODY
    # =========================================================
    def _leer_json(self):

        body = request.httprequest.data

        if not body:
            return {}

        if isinstance(body, bytes):
            body = body.decode('utf-8')

        return json.loads(body)


    # =========================================================
    # CREAR CLIENTE
    # =========================================================
    @http.route(
        ['/api/clientes', '/api/clientes/'],
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False
    )
    def crear_cliente(self, **kwargs):

        try:

            data = self._leer_json()

            if not data:
                return request.make_json_response({
                    'success': False,
                    'error': 'No se recibieron datos'
                }, status=400)

            cliente = request.env[
                'techstore.cliente'
            ].sudo().create({

                'name': data.get('name'),
                'cedula': data.get('cedula'),
                'email': data.get('email'),
                'telefono': data.get('telefono'),
                'activo': data.get('activo', True),

            })

            return request.make_json_response({
                'success': True,
                'id': cliente.id,
                'message': 'Cliente creado correctamente'
            })

        except (TypeError, ValueError, ValidationError) as e:
            return request.make_json_response({
                'success': False,
                'error': str(e)
            }, status=400)
        except Exception as e:

            return request.make_json_response({
                'success': False,
                'error': str(e)
            }, status=500)


    # =========================================================
    # CREAR PRODUCTO
    # =========================================================
    @http.route(
        ['/api/productos', '/api/productos/'],
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False
    )
    def crear_producto(self, **kwargs):

        try:

            data = self._leer_json()

            if not data:
                return request.make_json_response({
                    'success': False,
                    'error': 'No se recibieron datos'
                }, status=400)

            producto = request.env[
                'techstore.producto'
            ].sudo().create({

                'name': data.get('name'),

                'codigo': data.get('codigo'),

                'precio_unitario': data.get(
                    'precio_unitario'
                ),

                'stock_disponible': data.get(
                    'stock_disponible',
                    10
                ),

                'activo': data.get(
                    'activo',
                    True
                ),

            })

            return request.make_json_response({
                'success': True,
                'id': producto.id,
                'message': 'Producto creado correctamente'
            })

        except (TypeError, ValueError, ValidationError) as e:
            return request.make_json_response({
                'success': False,
                'error': str(e)
            }, status=400)
        except Exception as e:

            return request.make_json_response({
                'success': False,
                'error': str(e)
            }, status=500)


    # =========================================================
    # CREAR VENTA
    # =========================================================
    @http.route(
        ['/api/ventas', '/api/ventas/'],
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False
    )
    def crear_venta(self, **kwargs):

        try:

            data = self._leer_json()

            if not data:
                return request.make_json_response({
                    'success': False,
                    'error': 'No se recibieron datos'
                }, status=400)

            venta = request.env[
                'techstore.venta'
            ].sudo().create({

                'name': data.get(
                    'name',
                    'Nueva venta'
                ),

                'cliente_id': data.get(
                    'cliente_id'
                ),

                'producto_id': data.get(
                    'producto_id'
                ),

                'cantidad': data.get(
                    'cantidad',
                    0
                ),

                'descuento': data.get(
                    'descuento',
                    0
                ),

                'iva_porcentaje': data.get(
                    'iva_porcentaje',
                    15.0
                ),

                'observacion': data.get(
                    'observacion'
                ),

            })

            return request.make_json_response({

                'success': True,

                'id': venta.id,

                'name': venta.name,

                'cliente_id': (
                    venta.cliente_id.id
                    if venta.cliente_id
                    else None
                ),

                'producto_id': (
                    venta.producto_id.id
                    if venta.producto_id
                    else None
                ),

                'cantidad': venta.cantidad,

                'precio_unitario':
                    venta.precio_unitario,

                'stock_disponible':
                    venta.stock_disponible,

                'descuento':
                    venta.descuento,

                'descuento_aplicado':
                    venta.descuento_aplicado,

                'iva_porcentaje':
                    venta.iva_porcentaje,

                'subtotal':
                    venta.subtotal,

                'iva':
                    venta.iva,

                'total':
                    venta.total,

                'tiempo_respuesta':
                    venta.tiempo_respuesta,

                'estado_calidad':
                    venta.estado_calidad,

                'message':
                    'Venta creada correctamente'

            })

        except (TypeError, ValueError, ValidationError) as e:
            return request.make_json_response({
                'success': False,
                'error': str(e)
            }, status=400)
        except Exception as e:

            return request.make_json_response({
                'success': False,
                'error': str(e)
            }, status=500)