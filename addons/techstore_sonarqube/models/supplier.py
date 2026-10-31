from odoo import api, fields, models
from odoo.exceptions import ValidationError


class TechstoreSupplier(models.Model):
    _name = 'techstore.supplier'
    _description = 'Proveedor'

    name = fields.Char(string='Nombre', required=True)
    tax_id = fields.Char(string='RUC / Identificación')
    email = fields.Char(string='Correo')
    phone = fields.Char(string='Teléfono')
    address = fields.Text(string='Dirección')
    active = fields.Boolean(default=True)

    @api.constrains('email')
    def _check_email(self):
        for supplier in self:
            if supplier.email and '@' not in supplier.email:
                raise ValidationError('Correo electrónico inválido')

    def get_contact_summary(self):
        for supplier in self:
            result = 'Nombre: ' + str(supplier.name)
            result = result + ' | Correo: ' + str(supplier.email)
            result = result + ' | Teléfono: ' + str(supplier.phone)
            result = result + ' | Dirección: ' + str(supplier.address)
            if supplier.active == True:
                result = result + ' | Estado: ACTIVO'
            else:
                result = result + ' | Estado: INACTIVO'
        return result
