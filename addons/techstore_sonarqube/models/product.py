from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

ERR_PRODUCT_NOT_FOUND = 'Producto no encontrado'


class TechstoreProduct(models.Model):
    _name = 'techstore.product'
    _description = 'Producto TechStore'
    _order = 'name'

    code = fields.Char(string='Código', required=True)
    name = fields.Char(string='Nombre', required=True)
    category_id = fields.Many2one('techstore.category', string='Categoría', required=True)
    supplier_id = fields.Many2one('techstore.supplier', string='Proveedor')
    description = fields.Text(string='Descripción')
    cost = fields.Float(string='Costo', default=0.0)
    price = fields.Float(string='Precio', required=True, default=0.0)
    stock = fields.Integer(string='Stock', default=0)
    minimum_stock = fields.Integer(string='Stock mínimo', default=5)
    status = fields.Selection([
        ('available', 'Disponible'),
        ('low', 'Stock bajo'),
        ('out', 'Agotado'),
    ], string='Estado', compute='_compute_status', store=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'El código del producto ya existe.'),
    ]

    @api.depends('stock', 'minimum_stock')
    def _compute_status(self):
        for product in self:
            if product.stock <= 0:
                product.status = 'out'
            elif product.stock <= product.minimum_stock:
                product.status = 'low'
            else:
                product.status = 'available'

    @api.constrains('price', 'cost', 'stock', 'minimum_stock')
    def _check_values(self):
        for product in self:
            if product.price < 0:
                raise ValidationError('El precio no puede ser negativo')
            if product.cost < 0:
                raise ValidationError('El costo no puede ser negativo')
            if product.stock < 0:
                raise ValidationError('El stock no puede ser negativo')
            if product.minimum_stock < 0:
                raise ValidationError('El stock mínimo no puede ser negativo')

    def action_add_stock(self):
        for product in self:
            product.stock += 1
        return True

    def action_remove_stock(self):
        for product in self:
            if product.stock <= 0:
                raise UserError('Producto no encontrado o sin stock disponible')
            product.stock -= 1
        return True

    def action_validate_product(self):
        for product in self:
            if not product.code or not product.name or not product.category_id:
                raise UserError(ERR_PRODUCT_NOT_FOUND)
            if product.price <= 0 or product.stock < 0:
                raise UserError(ERR_PRODUCT_NOT_FOUND)
        return True

    def get_product_message(self):
        self.ensure_one()
        return f'Producto: {self.name} | Código: {self.code} | Precio: {self.price} | Stock: {self.stock} | Estado: {self.status}'

    def action_quality_demo(self):
        for product in self:
            is_valid = (
                product.active
                and product.stock > 0
                and product.price > 0
                and product.code
                and product.name
            )
            product.description = 'Producto válido para la venta' if is_valid else ERR_PRODUCT_NOT_FOUND
        return True