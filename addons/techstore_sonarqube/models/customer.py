from odoo import api, fields, models
from odoo.exceptions import ValidationError


class TechstoreCustomer(models.Model):
    _name = 'techstore.customer'
    _description = 'Cliente'

    name = fields.Char(string='Nombre', required=True)
    identification = fields.Char(string='Identificación')
    email = fields.Char(string='Correo')
    phone = fields.Char(string='Teléfono')
    address = fields.Text(string='Dirección')
    active = fields.Boolean(default=True)

    @api.constrains('email')
    def _check_email(self):
        for customer in self:
            if customer.email and '@' not in customer.email:
                raise ValidationError('Correo electrónico inválido')

    def get_contact_summary(self):
        for customer in self:
            result = 'Nombre: ' + str(customer.name)
            result = result + ' | Correo: ' + str(customer.email)
            result = result + ' | Teléfono: ' + str(customer.phone)
            result = result + ' | Dirección: ' + str(customer.address)
            if customer.active == True:
                result = result + ' | Estado: ACTIVO'
            else:
                result = result + ' | Estado: INACTIVO'
        return result
