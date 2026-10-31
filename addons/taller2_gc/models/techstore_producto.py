import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class TechstoreProducto(models.Model):
    _name = 'techstore.producto'
    _description = 'Producto TechStore'
    _order = 'name'

    _sql_constraints = [
        (
            'codigo_unique',
            'UNIQUE(codigo)',
            'El código del producto ya está registrado. No puede haber productos duplicados.',
        ),
    ]

    name = fields.Char(string='Producto', required=True, size=100)
    codigo = fields.Char(string='Código', required=True)
    precio_unitario = fields.Float(
        string='Precio unitario',
        required=True,
        default=0,
        digits=(16, 2),
    )
    stock_disponible = fields.Integer(string='Stock disponible', default=10)
    activo = fields.Boolean(string='Activo', default=True)

    @api.constrains('codigo', 'precio_unitario', 'stock_disponible')
    def _check_values(self):
        for rec in self:
            if not rec.codigo or not re.fullmatch(r'[A-Za-z0-9]{1,8}', rec.codigo):
                raise ValidationError(
                    'El código solo puede contener letras y números, con máximo 8 caracteres.'
                )
            if rec.precio_unitario < 0:
                raise ValidationError('El precio unitario no puede ser negativo.')
            if rec.precio_unitario > 99999.99:
                raise ValidationError(
                    'El precio unitario no puede superar 99.999,99.'
                )
            if rec.stock_disponible < 0:
                raise ValidationError('El stock disponible no puede ser negativo.')
            if rec.stock_disponible > 1000:
                raise ValidationError(
                    'El stock disponible no puede superar 1000 unidades.'
                )
            if self.search_count([
                ('codigo', '=', rec.codigo),
                ('id', '!=', rec.id),
            ]):
                raise ValidationError(
                    'El código del producto ya está registrado. '
                    'No puede haber productos duplicados.'
                )

    @api.model
    def create(self, vals):
        stock = vals.get('stock_disponible', 10)
        if stock <= 0:
            raise ValidationError(
                'El stock disponible debe ser mayor que cero al crear un producto.'
            )
        return super().create(vals)
