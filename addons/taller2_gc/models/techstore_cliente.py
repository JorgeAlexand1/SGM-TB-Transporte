import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class TechstoreCliente(models.Model):
    _name = 'techstore.cliente'
    _description = 'Cliente TechStore'
    _order = 'name'

    _sql_constraints = [
        (
            'cedula_unique',
            'UNIQUE(cedula)',
            'La cédula ya está registrada. No puede haber clientes duplicados.',
        ),
    ]

    name = fields.Char(string='Nombre del cliente', required=True, size=100)
    cedula = fields.Char(string='Cédula/RUC', required=True, size=10)
    email = fields.Char(string='Correo', required=True, size=254)
    telefono = fields.Char(string='Teléfono', required=True, size=10)
    activo = fields.Boolean(string='Activo', default=True)

    @api.constrains('name', 'cedula', 'email', 'telefono')
    def _check_contact_data(self):
        for rec in self:
            if not rec.name or not re.fullmatch(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]+", rec.name.strip()):
                raise ValidationError(
                    'El nombre del cliente solo puede contener letras y espacios.'
                )
            if not rec.cedula or not re.fullmatch(r'\d{10}', rec.cedula):
                raise ValidationError(
                    'La cédula debe contener exactamente 10 dígitos numéricos.'
                )
            if not rec.telefono or not re.fullmatch(r'\d{10}', rec.telefono):
                raise ValidationError(
                    'El teléfono debe contener exactamente 10 dígitos numéricos.'
                )
            if not re.fullmatch(
                r'[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+'
                r'@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.com',
                rec.email,
                re.IGNORECASE,
            ):
                raise ValidationError(
                    'El correo debe tener un formato válido y terminar en .com.'
                )
            if self.search_count([
                ('cedula', '=', rec.cedula),
                ('id', '!=', rec.id),
            ]):
                raise ValidationError(
                    'La cédula ya está registrada. No puede haber clientes duplicados.'
                )
