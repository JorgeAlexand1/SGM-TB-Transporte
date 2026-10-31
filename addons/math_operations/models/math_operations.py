# -*- coding: utf-8 -*-

from math import sqrt

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class MathOperation(models.Model):
    _name = 'math.operation'
    _description = 'Mathematical Operations'

    name = fields.Char('Operation ID', readonly=True, copy=False, default='New')
    operand_1 = fields.Float('First Operand', required=True)
    operand_2 = fields.Float('Second Operand', required=True)
    operation_type = fields.Selection([
        ('add', 'Addition'),
        ('subtract', 'Subtraction'),
        ('multiply', 'Multiplication'),
        ('divide', 'Division'),
        ('power', 'Power'),
        ('sqrt', 'Square Root'),
        ('avg', 'Average'),
        ('percent', 'Percentage'),
    ], 'Operation', required=True)
    estado = fields.Selection([
        ('correcto', 'Correcto'),
        ('error', 'Error detectado'),
    ], default='correcto', required=True)
    result = fields.Float('Result', readonly=True, compute='_compute_result', store=True)
    operation_date = fields.Datetime('Operation Date', default=fields.Datetime.now)
    user_id = fields.Many2one('res.users', 'User', default=lambda self: self.env.user)
    notes = fields.Text('Notes')

    @api.depends('operand_1', 'operand_2', 'operation_type')
    def _compute_result(self):
        for record in self:
            if record.operation_type == 'add':
                record.result = record.operand_1 + record.operand_2
            elif record.operation_type == 'subtract':
                record.result = record.operand_1 - record.operand_2
            elif record.operation_type == 'multiply':
                record.result = record.operand_1 * record.operand_2
            elif record.operation_type == 'divide':
                record.result = record.operand_1 / record.operand_2
            elif record.operation_type == 'power':
                record.result = record.operand_1 ** record.operand_2
            elif record.operation_type == 'sqrt':
                record.result = sqrt(record.operand_1)
            elif record.operation_type == 'avg':
                record.result = (record.operand_1 + record.operand_2) / 2
            elif record.operation_type == 'percent':
                record.result = record.operand_1 * record.operand_2 / 100
            else:
                record.result = 0

    @api.constrains('operand_1', 'operand_2', 'operation_type')
    def _check_operation_values(self):
        for record in self:
            if record.operation_type == 'divide' and record.operand_2 == 0:
                raise ValidationError('Division by zero is not allowed.')
            if record.operation_type == 'sqrt' and record.operand_1 < 0:
                raise ValidationError('Square root of a negative number is not allowed.')