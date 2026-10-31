from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

class TestMathOperation(TransactionCase):
    
    def setUp(self):
        super().setUp()
        self.MathOperation = self.env['math.operation']
    
    def test_sum_operation(self):
        op = self.MathOperation.create({
            'operand_1' : 2,
            'operand_2': 5,
            'operation_type': 'add',
        })
        self.assertEqual(op.result, 7)
    
    def test_subtract_operation(self):
        op = self.MathOperation.create({
            'operand_1' : 10,
            'operand_2': 4,
            'operation_type': 'subtract',
        })
        self.assertEqual(op.result, 6)
        
    def test_multiply_operation(self):
        op = self.MathOperation.create({
            'operand_1' : 3,
            'operand_2': 5,
            'operation_type': 'multiply',
        })
        self.assertEqual(op.result, 15)
        
    def test_divide_operation(self):
        op = self.MathOperation.create({
            'operand_1' : 20,
            'operand_2': 4,
            'operation_type': 'divide',
        })
        self.assertEqual(op.result, 5)

    def test_divide_by_zero(self):
        with self.assertRaises(ValidationError):
            self.MathOperation.create({
                'operand_1': 20,
                'operand_2': 0,
                'operation_type': 'divide',
            })

    def test_power_operation(self):
        op = self.MathOperation.create({
            'operand_1': 2,
            'operand_2': 3,
            'operation_type': 'power',
        })
        self.assertEqual(op.result, 8)

    def test_square_root_operation(self):
        op = self.MathOperation.create({
            'operand_1': 81,
            'operand_2': 0,
            'operation_type': 'sqrt',
        })
        self.assertEqual(op.result, 9)

    def test_square_root_negative_number(self):
        with self.assertRaises(ValidationError):
            self.MathOperation.create({
                'operand_1': -1,
                'operand_2': 0,
                'operation_type': 'sqrt',
            })

    def test_average_operation(self):
        op = self.MathOperation.create({
            'operand_1': 6,
            'operand_2': 10,
            'operation_type': 'avg',
        })
        self.assertEqual(op.result, 8)

    def test_percentage_operation(self):
        op = self.MathOperation.create({
            'operand_1': 200,
            'operand_2': 15,
            'operation_type': 'percent',
        })
        self.assertEqual(op.result, 30)

    def test_default_state(self):
        op = self.MathOperation.create({
            'operand_1': 2,
            'operand_2': 3,
            'operation_type': 'add',
        })
        self.assertEqual(op.estado, 'correcto')