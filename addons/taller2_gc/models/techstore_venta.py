from odoo import api, fields, models
from odoo.exceptions import ValidationError
import random


class TechstoreVenta(models.Model):
    _name = 'techstore.venta'
    _description = 'Venta TechStore'
    _order = 'create_date desc'

    _sql_constraints = [
        (
            'name_unique',
            'UNIQUE(name)',
            'La referencia de venta ya está registrada. No puede haber ventas duplicadas.',
        ),
    ]

    name = fields.Char(string='Referencia', required=True, default='Nueva venta', size=50)

    cliente_id = fields.Many2one(
        'techstore.cliente',
        string='Cliente',
        required=True
    )

    producto_id = fields.Many2one(
        'techstore.producto',
        string='Producto',
        required=True
    )

    cantidad = fields.Integer(string='Cantidad', required=True, default=1)
    precio_unitario = fields.Float(string='Precio unitario', required=True, readonly=True)
    stock_disponible = fields.Integer(string='Stock disponible', readonly=True)
    descuento = fields.Float(string='Descuento (%)', default=0, digits=(5, 2))
    iva_porcentaje = fields.Float(
        string='IVA (%)',
        default=15.0,
        digits=(5, 2),
    )
    descuento_aplicado = fields.Float(
        string='Descuento aplicado',
        compute='_compute_subtotales',
        store=True,
        digits=(16, 2),
    )
    subtotal = fields.Float(string='Subtotal', compute='_compute_subtotales', store=True)
    iva = fields.Float(string='IVA', compute='_compute_totales', store=True)
    total = fields.Float(string='Total', compute='_compute_totales', store=True)
    tiempo_respuesta = fields.Float(string='Tiempo de respuesta')
    estado_calidad = fields.Selection([
        ('pendiente', 'Pendiente'),
        ('observado', 'Observado'),
        ('aceptable', 'Aceptable'),
    ], string='Estado de calidad', default='pendiente')

    observacion = fields.Text(string='Observación del estudiante')

    @api.onchange('producto_id')
    def _onchange_producto_id(self):
        for rec in self:
            if rec.producto_id:
                rec.precio_unitario = rec.producto_id.precio_unitario
                rec.stock_disponible = rec.producto_id.stock_disponible

    @api.depends('cantidad', 'precio_unitario', 'descuento')
    def _compute_subtotales(self):
        for rec in self:
            bruto = rec.cantidad * rec.precio_unitario
            rec.descuento_aplicado = bruto * rec.descuento / 100
            rec.subtotal = bruto - rec.descuento_aplicado

    @api.depends('subtotal', 'iva_porcentaje')
    def _compute_totales(self):
        for rec in self:
            rec.iva = rec.subtotal * (rec.iva_porcentaje / 100)
            rec.total = rec.subtotal + rec.iva

    @api.constrains('cantidad', 'descuento', 'precio_unitario', 'iva_porcentaje')
    def _check_importes(self):
        for rec in self:
            if rec.cantidad <= 0:
                raise ValidationError('La cantidad debe ser mayor que cero.')
            if rec.cantidad > 999999:
                raise ValidationError('La cantidad no puede superar 999999 unidades.')
            if rec.descuento < 0:
                raise ValidationError('El descuento no puede ser negativo.')
            if rec.descuento > 100:
                raise ValidationError('El descuento debe estar entre 0% y 100%.')
            if rec.iva_porcentaje < 0 or rec.iva_porcentaje > 100:
                raise ValidationError('El IVA debe estar entre 0% y 100%.')

    @api.constrains('name')
    def _check_unique_name(self):
        for rec in self:
            if self.search_count([
                ('name', '=', rec.name),
                ('id', '!=', rec.id),
            ]):
                raise ValidationError(
                    'La referencia de venta ya está registrada. '
                    'No puede haber ventas duplicadas.'
                )

    @api.model
    def create(self, vals):
        name = vals.get('name', 'Nueva venta')
        if self.search_count([('name', '=', name)]):
            raise ValidationError(
                'La referencia de venta ya está registrada. '
                'No puede haber ventas duplicadas.'
            )

        cliente = self.env['techstore.cliente'].browse(vals.get('cliente_id'))
        producto_id = vals.get('producto_id')
        producto = self.env['techstore.producto'].browse(producto_id)

        if not cliente.exists() or not cliente.activo:
            raise ValidationError('Debe seleccionar un cliente activo.')
        if not producto.exists() or not producto.activo:
            raise ValidationError('Debe seleccionar un producto activo.')

        self.env.cr.execute(
            'SELECT id FROM techstore_producto WHERE id = %s FOR UPDATE',
            (producto.id,),
        )
        producto.invalidate_recordset()
        cantidad = vals.get('cantidad', 0)
        descuento = vals.get('descuento', 0)
        iva_porcentaje = vals.get('iva_porcentaje', 15.0)
        importe_bruto = cantidad * producto.precio_unitario

        if cantidad <= 0:
            raise ValidationError('La cantidad debe ser mayor que cero.')
        if cantidad > 999999:
            raise ValidationError('La cantidad no puede superar 999999 unidades.')
        if descuento < 0 or descuento > 100:
            raise ValidationError(
                'El descuento debe estar entre 0% y 100%.'
            )
        if iva_porcentaje < 0 or iva_porcentaje > 100:
            raise ValidationError('El IVA debe estar entre 0% y 100%.')
        if cantidad > producto.stock_disponible:
            raise ValidationError(
                'Stock insuficiente. Disponible: %s.' % producto.stock_disponible
            )

        vals['precio_unitario'] = producto.precio_unitario
        vals['stock_disponible'] = producto.stock_disponible
        vals['tiempo_respuesta'] = random.uniform(0.10, 3.50)
        vals['estado_calidad'] = 'observado'

        venta = super().create(vals)
        producto.stock_disponible -= cantidad
        return venta

    def write(self, vals):
        protected = {'cliente_id', 'producto_id', 'cantidad', 'precio_unitario'}
        if protected.intersection(vals):
            raise ValidationError(
                'No se puede cambiar el cliente, producto, cantidad o precio '
                'de una venta registrada.'
            )
        return super().write(vals)

    def unlink(self):
        for venta in self:
            producto = venta.producto_id
            self.env.cr.execute(
                'SELECT id FROM techstore_producto WHERE id = %s FOR UPDATE',
                (producto.id,),
            )
            producto.invalidate_recordset()
            producto.stock_disponible += venta.cantidad
        return super().unlink()

    def action_marcar_aceptable(self):
        for rec in self:
            rec.estado_calidad = 'aceptable'

    def action_marcar_observado(self):
        for rec in self:
            rec.estado_calidad = 'observado'
