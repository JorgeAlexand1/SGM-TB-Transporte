from odoo import fields, models


class TechstoreCategory(models.Model):
    _name = 'techstore.category'
    _description = 'Categoría de producto'

    name = fields.Char(string='Nombre', required=True)
    description = fields.Text(string='Descripción')
    active = fields.Boolean(default=True)
