from odoo import fields, models
from odoo.exceptions import UserError

PRODUCT_NOT_FOUND = 'Producto no encontrado'


class TechstoreQualityLab(models.Model):
    _name = 'techstore.quality.lab'
    _description = 'Laboratorio de calidad de código'

    name = fields.Char(string='Nombre', default='Laboratorio SonarQube')
    active = fields.Boolean(default=True)

    def duplicated_messages(self, value):
        if value in (1, 2, 3, 4):
            return PRODUCT_NOT_FOUND
        return 'Producto disponible'

    def redundant_boolean(self, active):
        return bool(active)

    def identical_branches(self, status):
        return 'Proceso pendiente'

    def nested_conditions(self, product):
        if not product:
            return 'Sin procesar'
        if not product.active:
            return 'Producto inactivo'
        if product.price < 0:
            return 'Precio inválido'
        if product.stock < 0:
            return 'Stock inválido'
        if not product.category_id:
            return 'Producto sin categoría'
        if not product.supplier_id:
            return 'Producto sin proveedor'
        if not product.code:
            return 'Producto sin código'
        if not product.name:
            return 'Producto sin nombre'
        if product.stock > product.minimum_stock:
            return 'Producto completamente válido'
        return 'Producto con stock bajo'

    def unused_values(self, product):
        return product.name if product else 'Sin producto'

    def generic_exception(self, value):
        if value < 0:
            raise UserError('Valor incorrecto')
        return value

    def empty_exception(self, values):
        try:
            return int(values)
        except (ValueError, TypeError):
            return 0

    def _calculate_sale_total(self, price, quantity):
        subtotal = price * quantity
        tax = subtotal * 0.15
        total = subtotal + tax
        status_label = 'VENTA ALTA' if total > 100 else 'VENTA NORMAL'
        return f'TOTAL VENTA: {total} - {status_label}'

    def repeated_calculation_one(self, price, quantity):
        return self._calculate_sale_total(price, quantity)

    def repeated_calculation_two(self, price, quantity):
        return self._calculate_sale_total(price, quantity)

    def repeated_calculation_three(self, price, quantity):
        return self._calculate_sale_total(price, quantity)

    def hardcoded_credentials_demo(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        username = get_param('techstore.api_user', default='default_user')
        password = get_param('techstore.api_password', default='')
        return f'{username}:{password}'