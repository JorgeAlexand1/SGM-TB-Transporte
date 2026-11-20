# -*- coding: utf-8 -*-
import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..lib import reglas

_logger = logging.getLogger(__name__)

PREFIJO = 'transporte_calidad.'
MAX_PUNTOS_TRAZADO = 400


class TransporteViaje(models.Model):
    _inherit = 'transporte.viaje'

    # ------------------------------------------------------------------ identificación de pruebas
    simulado = fields.Boolean(
        string='Datos simulados', readonly=True, copy=False, index=True,
        help='Recorrido generado para probar un escenario. Nunca se presenta como dato real.')
    escenario_simulado = fields.Char(string='Escenario de prueba', readonly=True, copy=False)
    incidencias_esperadas = fields.Char(
        string='Incidencias esperadas', copy=False,
        help="Códigos separados por coma de las incidencias que el escenario DEBE producir "
             "('ninguna' si debe cumplir). Se usa para medir el % de detección correcta.")

    # ------------------------------------------------------------------ resultado
    resultado = fields.Selection(
        [('sin_evaluar', 'Sin evaluar'), ('en_curso', 'En curso'), ('cumple', 'Cumple'), ('incumple', 'Incumple')],
        string='Resultado', default='sin_evaluar', readonly=True, copy=False, index=True, tracking=True)
    evaluado_en = fields.Datetime(string='Evaluado el', readonly=True, copy=False)
    tiene_gps = fields.Boolean(string='Con telemetría', readonly=True, copy=False)
    completo = fields.Boolean(string='Recorrido completo', readonly=True, copy=False)
    puntual = fields.Boolean(string='Puntual', readonly=True, copy=False)
    cumple_ruta = fields.Boolean(string='Cumple la ruta', readonly=True, copy=False)
    desviado = fields.Boolean(string='Desviado', readonly=True, copy=False)

    # ------------------------------------------------------------------ indicadores del viaje
    paradas_omitidas = fields.Integer(string='Paradas omitidas', readonly=True, copy=False)
    paradas_puntuales = fields.Integer(string='Paradas puntuales', readonly=True, copy=False)
    paradas_atrasadas = fields.Integer(string='Paradas atrasadas', readonly=True, copy=False)
    porcentaje_paradas = fields.Float(string='% paradas cumplidas', readonly=True, copy=False,
                                      digits=(5, 2), group_operator='avg')
    porcentaje_puntualidad = fields.Float(string='% puntualidad en paradas', readonly=True, copy=False,
                                          digits=(5, 2), group_operator='avg')
    retraso_inicio_min = fields.Float(string='Retraso de salida (min)', readonly=True, copy=False,
                                      digits=(10, 1), group_operator='avg')
    retraso_llegada_min = fields.Float(string='Retraso de llegada (min)', readonly=True, copy=False,
                                       digits=(10, 1), group_operator='avg')
    retraso_promedio_min = fields.Float(string='Retraso promedio en paradas (min)', readonly=True, copy=False,
                                        digits=(10, 1), group_operator='avg')
    retraso_maximo_min = fields.Float(string='Retraso máximo (min)', readonly=True, copy=False,
                                      digits=(10, 1), group_operator='max')
    retraso_acumulado_min = fields.Float(string='Retraso acumulado actual (min)', readonly=True, copy=False,
                                         digits=(10, 1), help='Retraso en la última parada visitada.')
    duracion_estimada_min = fields.Float(string='Duración estimada (min)', readonly=True, copy=False,
                                         digits=(10, 1), group_operator='avg')
    duracion_real_min = fields.Float(string='Duración real (min)', readonly=True, copy=False,
                                     digits=(10, 1), group_operator='avg')
    diferencia_duracion_min = fields.Float(string='Diferencia de duración (min)', readonly=True, copy=False,
                                           digits=(10, 1), group_operator='avg')
    diferencia_duracion_pct = fields.Float(string='Diferencia de duración (%)', readonly=True, copy=False,
                                           digits=(10, 1), group_operator='avg')
    distancia_estimada_km = fields.Float(string='Distancia estimada (km)', readonly=True, copy=False,
                                         digits=(10, 3))
    diferencia_distancia_km = fields.Float(string='Diferencia de distancia (km)', readonly=True, copy=False,
                                           digits=(10, 3), group_operator='avg')
    diferencia_distancia_pct = fields.Float(string='Diferencia de distancia (%)', readonly=True, copy=False,
                                            digits=(10, 1), group_operator='avg')
    max_desviacion_m = fields.Float(string='Alejamiento máximo del trazado (m)', readonly=True, copy=False,
                                    digits=(10, 1), group_operator='max')
    porcentaje_fuera_corredor = fields.Float(string='% posiciones fuera del corredor', readonly=True,
                                             copy=False, digits=(5, 2), group_operator='avg')
    huecos_senal = fields.Integer(string='Interrupciones de señal', readonly=True, copy=False)
    max_hueco_senal_min = fields.Float(string='Mayor interrupción (min)', readonly=True, copy=False, digits=(10, 1))

    # ------------------------------------------------------------------ incidencias y verificación
    incidencia_ids = fields.One2many('transporte.incidencia', 'viaje_id', string='Incidencias')
    incidencia_count = fields.Integer(string='Nº incidencias', compute='_compute_incidencia_count')
    deteccion_correcta = fields.Selection(
        [('na', 'No aplica'), ('correcta', 'Correcta'), ('incorrecta', 'Incorrecta')],
        string='Detección vs. esperado', default='na', readonly=True, copy=False)
    deteccion_detalle = fields.Char(string='Diferencias de detección', readonly=True, copy=False)

    @api.depends('incidencia_ids')
    def _compute_incidencia_count(self):
        for rec in self:
            rec.incidencia_count = len(rec.incidencia_ids)

    @api.constrains('incidencias_esperadas')
    def _check_incidencias_esperadas(self):
        for rec in self:
            try:
                reglas.parsear_tipos(rec.incidencias_esperadas)
            except ValueError as exc:
                raise ValidationError(str(exc))

    # ------------------------------------------------------------------ parámetros
    @api.model
    def _tolerancias(self):
        param = self.env['ir.config_parameter'].sudo()
        tol = {}
        for clave, defecto in reglas.TOLERANCIAS_DEFECTO.items():
            try:
                tol[clave] = float(param.get_param(PREFIJO + clave, defecto))
            except (TypeError, ValueError):
                tol[clave] = defecto
        return tol

    def _tiene_telemetria(self):
        self.ensure_one()
        return bool(self.simulado or self.vehicle_id.traccar_device_id or self.posicion_ids)

    def _datos_evaluacion(self, tol):
        self.ensure_one()
        tiene_gps = self._tiene_telemetria()
        validas = self.posicion_ids.filtered('valida').sorted(lambda p: (p.fecha_gps, p.id))
        return {
            'estado': self.state,
            'salida_plan': self.hora_salida_planificada,
            'llegada_plan': self.hora_llegada_planificada,
            'salida_real': self.hora_salida_real,
            'llegada_real': self.hora_llegada_real,
            'paradas': [{'id': l.id, 'secuencia': l.secuencia, 'estado': l.estado_parada,
                         'hora_plan': l.hora_planificada, 'hora_real': l.hora_llegada_real}
                        for l in self.parada_line_ids],
            'tiene_gps': tiene_gps,
            'posiciones': [(p.fecha_gps, p.latitud, p.longitud) for p in validas],
            'trazado': self.ruta_id._trazado_evaluacion(),
            'ancho_corredor_m': self.ruta_id.ancho_corredor_m or tol['ancho_corredor_m'],
            'distancia_estimada_km': self.ruta_id.distancia_estimada_km,
            'distancia_recorrida_km': self.distancia_recorrida_km if (tiene_gps and validas) else None,
            'ahora': fields.Datetime.now(),
        }

    # ------------------------------------------------------------------ evaluación
    def _evaluar_calidad(self):
        """Evalúa los viajes iniciados: guarda indicadores, puntualidad por parada e incidencias."""
        tol = self._tolerancias()
        for rec in self.sudo():
            if not rec.hora_salida_real or rec.state not in ('in_progress', 'completed', 'cancelled'):
                continue
            r = reglas.evaluar_viaje(rec._datos_evaluacion(tol), tol)
            for fila in r['filas']:
                linea = rec.parada_line_ids.filtered(lambda l, i=fila['id']: l.id == i)
                if linea.puntualidad != fila['clase']:
                    linea.write({'puntualidad': fila['clase']})
            rec._sincronizar_incidencias(r['incidencias'])
            vals = rec._valores_evaluacion(r)
            vals.update(rec._valores_deteccion(r))
            rec.write(vals)
        return True

    @staticmethod
    def _num(valor):
        return valor if valor is not None else 0.0

    def _valores_evaluacion(self, r):
        n = self._num
        return {
            'resultado': r['resultado'], 'evaluado_en': fields.Datetime.now(),
            'tiene_gps': bool(self._tiene_telemetria()), 'completo': r['completo'], 'puntual': r['puntual'],
            'cumple_ruta': r['cumple_ruta'], 'desviado': r['desviado'],
            'paradas_omitidas': r['paradas_omitidas'], 'paradas_puntuales': r['paradas_puntuales'],
            'paradas_atrasadas': r['paradas_atrasadas'],
            'porcentaje_paradas': n(r['porcentaje_paradas']),
            'porcentaje_puntualidad': n(r['porcentaje_puntualidad']),
            'retraso_inicio_min': n(r['retraso_inicio_min']),
            'retraso_llegada_min': n(r['retraso_llegada_min']),
            'retraso_promedio_min': n(r['retraso_promedio_min']),
            'retraso_maximo_min': n(r['retraso_maximo_min']),
            'retraso_acumulado_min': n(r['retraso_acumulado_min']),
            'duracion_estimada_min': n(r['duracion_estimada_min']),
            'duracion_real_min': n(r['duracion_real_min']),
            'diferencia_duracion_min': n(r['diferencia_duracion_min']),
            'diferencia_duracion_pct': n(r['diferencia_duracion_pct']),
            'distancia_estimada_km': n(r['distancia_estimada_km']),
            'diferencia_distancia_km': n(r['diferencia_distancia_km']),
            'diferencia_distancia_pct': n(r['diferencia_distancia_pct']),
            'max_desviacion_m': n(r['max_desviacion_m']),
            'porcentaje_fuera_corredor': n(r['porcentaje_fuera_corredor']),
            'huecos_senal': r['huecos_senal'], 'max_hueco_senal_min': n(r['max_hueco_senal_min']),
        }

    def _valores_deteccion(self, r):
        if not self.incidencias_esperadas or r['resultado'] == 'en_curso':
            return {'deteccion_correcta': 'na', 'deteccion_detalle': False}
        comp = reglas.comparar_deteccion(reglas.parsear_tipos(self.incidencias_esperadas),
                                         {i['tipo'] for i in r['incidencias']})
        detalle = []
        if comp['falsos_positivos']:
            detalle.append(_('No esperadas: %s') % ', '.join(comp['falsos_positivos']))
        if comp['falsos_negativos']:
            detalle.append(_('No detectadas: %s') % ', '.join(comp['falsos_negativos']))
        return {'deteccion_correcta': 'correcta' if comp['correcta'] else 'incorrecta',
                'deteccion_detalle': ' · '.join(detalle) or False}

    def _fecha_incidencia(self, inc):
        linea = self.parada_line_ids.filtered(lambda l: l.id == inc.get('ref'))
        if linea:
            return linea.hora_llegada_real or linea.hora_planificada
        if inc['tipo'] == 'retraso_inicio':
            return self.hora_salida_real
        return self.hora_llegada_real or self.hora_salida_real

    def _sincronizar_incidencias(self, detectadas):
        """Idempotente: actualiza las existentes, crea las nuevas y elimina las abiertas que ya no aplican.

        Las incidencias que un usuario ya gestionó (en atención/resuelta/descartada) nunca se borran.
        """
        self.ensure_one()
        Incidencia = self.env['transporte.incidencia'].sudo()
        existentes = {(i.tipo, i.viaje_parada_id.id or False): i
                      for i in self.incidencia_ids.filtered(lambda i: i.origen == 'automatica')}
        vistas = set()
        for inc in detectadas:
            clave = (inc['tipo'], inc.get('ref') or False)
            vistas.add(clave)
            vals = {'severidad': inc['severidad'], 'valor': inc['valor'] or 0.0, 'unidad': inc['unidad'],
                    'descripcion': inc['descripcion'], 'regla': inc['regla']}
            if clave in existentes:
                existentes[clave].write(vals)
            else:
                linea = self.parada_line_ids.filtered(lambda l, ref=inc.get('ref'): l.id == ref)
                vals.update({'tipo': inc['tipo'], 'origen': 'automatica', 'viaje_id': self.id,
                             'viaje_parada_id': linea.id or False, 'parada_id': linea.parada_id.id or False,
                             'fecha': self._fecha_incidencia(inc) or fields.Datetime.now()})
                Incidencia.create(vals)
        obsoletas = Incidencia.browse([i.id for k, i in existentes.items()
                                       if k not in vistas and i.estado == 'abierta'])
        obsoletas.with_context(reevaluacion=True).unlink()

    # ------------------------------------------------------------------ ganchos del ciclo de vida
    def action_completar(self):
        res = super().action_completar()
        self._evaluar_calidad()
        return res

    def action_cancelar(self):
        res = super().action_cancelar()
        self.filtered('hora_salida_real')._evaluar_calidad()
        return res

    def action_borrador(self):
        res = super().action_borrador()
        self.mapped('incidencia_ids').filtered(lambda i: i.origen == 'automatica').with_context(
            reevaluacion=True).unlink()
        self.write({'resultado': 'sin_evaluar', 'evaluado_en': False, 'deteccion_correcta': 'na'})
        return res

    def _procesar_geocercas(self, posiciones):
        res = super()._procesar_geocercas(posiciones)
        self._evaluar_calidad()
        return res

    @api.model
    def _cron_evaluar_viajes(self):
        viajes = self.search(['|', ('state', '=', 'in_progress'),
                              '&', ('state', 'in', ('completed', 'cancelled')),
                              ('resultado', '=', 'sin_evaluar'),
                              ('hora_salida_real', '!=', False)])
        viajes._evaluar_calidad()

    @api.model
    def _reevaluar_todos(self):
        viajes = self.search([('hora_salida_real', '!=', False),
                              ('state', 'in', ('in_progress', 'completed', 'cancelled'))])
        viajes._evaluar_calidad()
        return len(viajes)

    # ------------------------------------------------------------------ acciones de UI
    def action_reevaluar(self):
        if not self.filtered('hora_salida_real'):
            raise UserError(_('Solo se evalúan viajes que ya iniciaron su recorrido.'))
        self._evaluar_calidad()

    def action_ver_incidencias(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Incidencias de %s') % self.name,
            'res_model': 'transporte.incidencia', 'view_mode': 'tree,form',
            'domain': [('viaje_id', '=', self.id)], 'context': {'default_viaje_id': self.id},
        }

    def action_usar_como_trazado(self):
        """Fija las posiciones de este viaje (cumplido) como trazado de referencia de su ruta."""
        self.ensure_one()
        validas = self.posicion_ids.filtered('valida').sorted(lambda p: (p.fecha_gps, p.id))
        if len(validas) < 2:
            raise UserError(_('El viaje no tiene posiciones GPS suficientes para generar un trazado.'))
        if self.resultado == 'incumple' and self.desviado:
            raise UserError(_('No use un recorrido desviado como referencia.'))
        paso = max(1, -(-len(validas) // MAX_PUNTOS_TRAZADO))
        puntos = [[round(p.latitud, 6), round(p.longitud, 6)] for p in validas[::paso]]
        if puntos[-1] != [round(validas[-1].latitud, 6), round(validas[-1].longitud, 6)]:
            puntos.append([round(validas[-1].latitud, 6), round(validas[-1].longitud, 6)])
        self.ruta_id.write({'trazado_referencia': json.dumps(puntos),
                            'trazado_origen': _('Viaje %s (%s puntos)') % (self.name, len(puntos))})
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': _('Trazado de referencia'), 'type': 'success', 'sticky': False,
                       'message': _('La ruta %s usa ahora el recorrido de %s como corredor.')
                                  % (self.ruta_id.name, self.name)},
        }
