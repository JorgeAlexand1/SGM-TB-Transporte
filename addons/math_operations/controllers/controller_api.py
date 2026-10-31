import json

from odoo import http
from odoo.http import request


class MathOperationAPI(http.Controller):

	_operation_types = {'add', 'subtract', 'multiply', 'divide', 'power', 'sqrt', 'avg', 'percent'}

	def _serialize_record(self, record):
		return {
			'id': record.id,
			'name': record.name,
			'operand_1': record.operand_1,
			'operand_2': record.operand_2,
			'operation_type': record.operation_type,
			'estado': record.estado,
			'result': record.result,
			'operation_date': record.operation_date,
			'user_id': record.user_id.id,
			'notes': record.notes,
		}

	def _json_body(self):
		payload = request.params or getattr(request, 'jsonrequest', None)
		if not payload:
			raw_body = request.httprequest.get_data(as_text=True)
			payload = json.loads(raw_body) if raw_body else {}
		if isinstance(payload, dict) and isinstance(payload.get('params'), dict):
			return payload['params']
		return payload if isinstance(payload, dict) else {}

	def _error(self, message, status=400):
		return {
			'success': False,
			'error': message,
			'status': status,
		}

	def _record_id(self, payload):
		record_id = payload.get('id')
		if isinstance(record_id, bool) or not isinstance(record_id, int):
			return None
		return record_id

	def _find_record(self, payload):
		record_id = self._record_id(payload)
		if record_id is None:
			return None
		return request.env['math.operation'].sudo().browse(record_id).exists()

	def _operation_values(self, payload, partial=False):
		values = {}
		for field_name in ('operand_1', 'operand_2'):
			if field_name in payload:
				value = payload[field_name]
				if isinstance(value, bool) or not isinstance(value, (int, float)):
					return None, '%s must be a number' % field_name
				values[field_name] = value

		if 'operation_type' in payload:
			operation_type = payload['operation_type']
			if operation_type not in self._operation_types:
				return None, 'operation_type must be one of: add, subtract, multiply, divide, power, sqrt, avg, percent'
			values['operation_type'] = operation_type

		if 'notes' in payload:
			values['notes'] = payload['notes']

		required_fields = ('operand_1', 'operand_2', 'operation_type')
		if not partial:
			missing = [field_name for field_name in required_fields if field_name not in values]
			if missing:
				return None, 'Missing required fields: %s' % ', '.join(missing)
		elif not values:
			return None, 'At least one field is required to update an operation'

		return values, None

	@http.route('/api/operations', type='json', auth='public', methods=['GET'], csrf=False)
	def get_operations(self, **kwargs):
		records = request.env['math.operation'].sudo().search([])
		data = [self._serialize_record(record) for record in records]
		return {'success': True, 'count': len(data), 'data': data}

	@http.route('/api/operations/create', type='json', auth='public', methods=['POST'], csrf=False)
	def create_operation(self, **kwargs):
		values, error = self._operation_values(self._json_body())
		if error:
			return self._error(error)

		record = request.env['math.operation'].sudo().create(values)
		return {'success': True, 'data': self._serialize_record(record)}

	@http.route('/api/operations/get', type='json', auth='public', methods=['GET', 'POST'], csrf=False)
	def get_operation(self, **kwargs):
		record = self._find_record(self._json_body())
		if not record:
			return self._error('Operation not found', 404)
		return {'success': True, 'data': self._serialize_record(record)}

	@http.route('/api/operations/update', type='json', auth='public', methods=['POST', 'PUT'], csrf=False)
	def update_operation(self, **kwargs):
		payload = self._json_body()
		record = self._find_record(payload)
		if not record:
			return self._error('Operation not found', 404)

		values, error = self._operation_values(payload, partial=True)
		if error:
			return self._error(error)

		record.write(values)
		return {'success': True, 'data': self._serialize_record(record)}

	@http.route('/api/operations/delete', type='json', auth='public', methods=['POST', 'DELETE'], csrf=False)
	def delete_operation(self, **kwargs):
		record = self._find_record(self._json_body())
		if not record:
			return self._error('Operation not found', 404)

		record.unlink()
		return {'success': True, 'id': record.id}
