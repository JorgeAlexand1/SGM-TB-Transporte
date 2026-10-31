from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

MODEL_TECHSTORE_SALE_ORDER = 'techstore.sale.order'


class TechstoreSaleOrder(models.Model):
    _name = MODEL_TECHSTORE_SALE_ORDER
    _description = 'Venta TechStore'
    _order = 'date desc'

    name = fields.Char(string='Número', required=True, copy=False, readonly=True, default='Nuevo')
    customer_id = fields.Many2one('techstore.customer', string='Cliente', required=True)
    date = fields.Datetime(string='Fecha', default=fields.Datetime.now, required=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmada'),
        ('cancelled', 'Cancelada'),
    ], default='draft', string='Estado')
    line_ids = fields.One2many('techstore.sale.order.line', 'order_id', string='Detalle')
    subtotal = fields.Float(string='Subtotal', compute='_compute_totals', store=True)
    tax = fields.Float(string='IVA', compute='_compute_totals', store=True)
    total = fields.Float(string='Total', compute='_compute_totals', store=True)
    note = fields.Text(string='Observación')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code(MODEL_TECHSTORE_SALE_ORDER) or 'Nuevo'
        return super().create(vals_list)

    @api.depends('line_ids.subtotal')
    def _compute_totals(self):
        for order in self:
            subtotal = sum(line.subtotal for line in order.line_ids)
            order.subtotal = subtotal
            order.tax = subtotal * 0.15
            order.total = subtotal + order.tax

    def action_confirm(self):
        for order in self:
            if not order.line_ids:
                raise UserError('La venta debe tener al menos un producto')
            if order.state != 'draft':
                raise UserError('La venta no se encuentra en borrador')

            for line in order.line_ids:
                if line.quantity <= 0:
                    raise UserError('Cantidad inválida')
                if line.product_id.stock < line.quantity:
                    raise UserError(f'Stock insuficiente para {line.product_id.name}')

            for line in order.line_ids:
                line.product_id.stock -= line.quantity

            order.state = 'confirmed'
        return True

    def action_cancel(self):
        for order in self:
            if order.state == 'confirmed':
                for line in order.line_ids:
                    line.product_id.stock += line.quantity
            order.state = 'cancelled'
        return True


class TechstoreSaleOrderLine(models.Model):
    _name = 'techstore.sale.order.line'
    _description = 'Detalle de venta TechStore'

    order_id = fields.Many2one(MODEL_TECHSTORE_SALE_ORDER, string='Venta', required=True, ondelete='cascade')
    product_id = fields.Many2one('techstore.product', string='Producto', required=True)
    quantity = fields.Integer(string='Cantidad', default=1, required=True)
    price = fields.Float(string='Precio', required=True)
    discount = fields.Float(string='Descuento %', default=0.0)
    subtotal = fields.Float(string='Subtotal', compute='_compute_subtotal', store=True)

    @api.onchange('product_id')
    def _onchange_product(self):
        if self.product_id:
            self.price = self.product_id.price

    @api.depends('quantity', 'price', 'discount')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price * (1 - (line.discount / 100.0))

    @api.constrains('quantity', 'price', 'discount')
    def _check_line(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError('La cantidad debe ser mayor que cero')
            if line.price < 0:
                raise ValidationError('El precio no puede ser negativo')
            if not (0 <= line.discount <= 100):
                raise ValidationError('El descuento debe estar entre 0 y 100')