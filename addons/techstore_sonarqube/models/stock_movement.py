from odoo import api, fields, models
from odoo.exceptions import ValidationError


class TechstoreStockMovement(models.Model):
    _name = 'techstore.stock.movement'
    _description = 'Movimiento de inventario'
    _order = 'date desc'

    product_id = fields.Many2one('techstore.product', string='Producto', required=True)
    movement_type = fields.Selection([
        ('in', 'Entrada'),
        ('out', 'Salida'),
    ], string='Tipo', required=True)
    quantity = fields.Integer(string='Cantidad', required=True, default=1)
    date = fields.Datetime(string='Fecha', default=fields.Datetime.now, required=True)
    note = fields.Char(string='Observación')

    @api.constrains('quantity')
    def _check_quantity(self):
        for movement in self:
            if movement.quantity <= 0:
                raise ValidationError('La cantidad debe ser mayor que cero')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for movement in records:
            if movement.movement_type == 'in':
                movement.product_id.stock = movement.product_id.stock + movement.quantity
            else:
                if movement.product_id.stock < movement.quantity:
                    raise ValidationError('Stock insuficiente')
                movement.product_id.stock = movement.product_id.stock - movement.quantity
        return records
