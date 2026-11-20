# -*- coding: utf-8 -*-
"""Cálculo en vivo de los indicadores del dashboard (A7/A8). Nada es estático: todo sale de la BD."""
import time
from collections import OrderedDict
from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.transporte_gps_traccar.lib import traccar_parser
from odoo.addons.transporte_gps_traccar.lib.traccar_client import TraccarError

from ..lib import reglas
from .transporte_incidencia import TIPOS

ETIQUETA_TIPO = dict(TIPOS)
ESTADOS_EVALUADOS = ('cumple', 'incumple')


class TransporteCalidadDashboard(models.AbstractModel):
    _name = 'transporte.calidad.dashboard'
    _description = 'Indicadores del Dashboard de Calidad'

    # ------------------------------------------------------------------ filtros
    @api.model
    def _rango(self, filtros):
        hoy = fields.Date.context_today(self)
        hasta = fields.Date.to_date(filtros.get('fecha_hasta')) if filtros.get('fecha_hasta') else hoy
        desde = fields.Date.to_date(filtros.get('fecha_desde')) if filtros.get('fecha_desde') else hasta - timedelta(days=29)
        if desde > hasta:
            raise UserError(_('La fecha inicial no puede ser posterior a la final.'))
        return desde, hasta

    @api.model
    def _dominio_viajes(self, filtros, desde, hasta):
        dom = [('fecha_viaje', '>=', desde), ('fecha_viaje', '<=', hasta)]
        if filtros.get('ruta_id'):
            dom.append(('ruta_id', '=', int(filtros['ruta_id'])))
        if filtros.get('vehicle_id'):
            dom.append(('vehicle_id', '=', int(filtros['vehicle_id'])))
        origen = filtros.get('datos') or 'todos'
        if origen == 'reales':
            dom.append(('simulado', '=', False))
        elif origen == 'simulados':
            dom.append(('simulado', '=', True))
        return dom

    @api.model
    def _dominio_incidencias(self, filtros, desde, hasta):
        dom = [('fecha_dia', '>=', desde), ('fecha_dia', '<=', hasta), ('estado', '!=', 'descartada')]
        if filtros.get('ruta_id'):
            dom.append(('ruta_id', '=', int(filtros['ruta_id'])))
        if filtros.get('vehicle_id'):
            dom.append(('vehicle_id', '=', int(filtros['vehicle_id'])))
        origen = filtros.get('datos') or 'todos'
        if origen == 'reales':
            dom.append(('simulado', '=', False))
        elif origen == 'simulados':
            dom.append(('simulado', '=', True))
        return dom

    # ------------------------------------------------------------------ filas para las fórmulas
    @api.model
    def _fila_kpi(self, v):
        """Traduce un viaje evaluado a la fila que espera reglas.calcular_kpis_transporte (None = no aplica)."""
        con_distancia = bool(v.distancia_estimada_km and v.distancia_recorrida_km)
        return {
            'paradas_programadas': v.total_paradas_viaje,
            'paradas_atendidas': v.paradas_atendidas,
            'paradas_puntuales': v.paradas_puntuales,
            'cumple_ruta': v.cumple_ruta,
            'puntual': v.puntual,
            'retraso_promedio_min': v.retraso_promedio_min if v.paradas_atendidas else None,
            'porcentaje_fuera_corredor': v.porcentaje_fuera_corredor if (v.tiene_gps and v.cantidad_posiciones) else None,
            'desviado': v.desviado,
            'max_desviacion_m': v.max_desviacion_m,
            'diferencia_distancia_km': v.diferencia_distancia_km if con_distancia else None,
            'diferencia_distancia_pct': v.diferencia_distancia_pct if con_distancia else None,
            'completo': v.completo,
            'duracion_real_min': v.duracion_real_min,
            'duracion_estimada_min': v.duracion_estimada_min,
        }

    @api.model
    def _resumen_grupo(self, viajes, incidencias, dias):
        k = reglas.calcular_kpis_transporte([self._fila_kpi(v) for v in viajes],
                                            [{'tipo': i.tipo} for i in incidencias], dias)
        return {
            'viajes': len(viajes),
            'cumplimiento': k['cumplimiento_rutas']['valor'],
            'puntualidad': k['puntualidad_paradas']['valor'],
            'puntualidad_viajes': k['puntualidad_viajes']['valor'],
            'retraso_promedio': k['retraso_promedio']['valor'],
            'paradas_cumplidas': k['paradas_cumplidas']['valor'],
            'tiempo_promedio': k['tiempo_promedio']['valor'],
            'distancia_km': round(sum(viajes.mapped('distancia_recorrida_km')), 2),
            'incidencias': len(incidencias),
        }

    # ------------------------------------------------------------------ bloques
    @api.model
    def _kpis_transporte(self, evaluados, incidencias, dias):
        k = reglas.calcular_kpis_transporte([self._fila_kpi(v) for v in evaluados],
                                            [{'tipo': i.tipo} for i in incidencias], dias)
        k['incidencias']['por_tipo'] = reglas.pareto(
            {ETIQUETA_TIPO.get(t, t): n for t, n in k['incidencias']['por_tipo'].items()})
        return k

    @api.model
    def _kpis_software(self, filtros, desde, hasta, viajes_dominio):
        Pos = self.env['transporte.gps.posicion'].sudo()
        ini = datetime.combine(desde, datetime.min.time()) - timedelta(hours=12)
        fin = datetime.combine(hasta, datetime.max.time()) + timedelta(hours=12)
        dom_pos = [('fecha_gps', '>=', ini), ('fecha_gps', '<=', fin)]
        if filtros.get('vehicle_id'):
            dom_pos.append(('vehicle_id', '=', int(filtros['vehicle_id'])))
        origen = filtros.get('datos') or 'todos'
        if origen in ('reales', 'simulados'):
            dom_pos.append(('simulado', '=', origen == 'simulados'))
        total_pos = Pos.search_count(dom_pos)
        validas = Pos.search_count(dom_pos + [('valida', '=', True)])

        Log = self.env['transporte.gps.sync.log'].sudo()
        dom_log = [('fecha', '>=', ini), ('fecha', '<=', fin)]
        logs = Log.search(dom_log)
        traidas = sum(logs.mapped('posiciones_traidas'))
        duplicados = sum(logs.mapped('duplicados_descartados'))

        Med = self.env['transporte.calidad.medicion'].sudo()
        exactitud = Med.search([('tipo', '=', 'exactitud_sync')], limit=1)
        tiempos = Med.search([('tipo', 'in', ('dashboard', 'mapa', 'consulta_viajes', 'prueba_rendimiento')),
                              ('fecha', '>=', fields.Datetime.now() - timedelta(days=30))])
        ms = tiempos.mapped('duracion_ms')

        con_esperado = viajes_dominio.filtered(lambda v: v.deteccion_correcta in ('correcta', 'incorrecta'))
        correctas = con_esperado.filtered(lambda v: v.deteccion_correcta == 'correcta')
        return {
            'integridad_gps': {'valor': reglas.porcentaje(validas, total_pos), 'num': validas, 'den': total_pos,
                               'duplicados_descartados': duplicados, 'traidas': traidas},
            'exactitud_sync': {'valor': exactitud.valor if exactitud else None,
                               'muestra': exactitud.registros if exactitud else 0,
                               'fecha': fields.Datetime.to_string(exactitud.fecha) if exactitud else False,
                               'sync_ok': reglas.porcentaje(len(logs.filtered('ok')), len(logs)),
                               'syncs': len(logs)},
            'tiempo_respuesta': {'valor': reglas.promedio(ms), 'p95': reglas.percentil(ms, 95),
                                 'mediciones': len(ms),
                                 'sync_ms': reglas.promedio(logs.mapped('duracion_ms'))},
            'deteccion_correcta': {'valor': reglas.porcentaje(len(correctas), len(con_esperado)),
                                   'num': len(correctas), 'den': len(con_esperado),
                                   'fallos': [{'id': v.id, 'name': v.name, 'detalle': v.deteccion_detalle or ''}
                                              for v in con_esperado - correctas]},
        }

    @api.model
    def _vehiculos(self, viajes_periodo):
        buses = self.env['fleet.vehicle'].search([('es_bus_pasajeros', '=', True)])
        Viaje = self.env['transporte.viaje']
        filas = []
        for b in buses:
            actual = Viaje.search([('vehicle_id', '=', b.id), ('state', '=', 'in_progress')], limit=1)
            fila = {
                'id': b.id, 'nombre': b.display_name, 'placa': b.license_plate or '',
                'estado': dict(b._fields['estado_operativo'].selection).get(b.estado_operativo),
                'senal': b.estado_senal, 'lat': b.ultima_latitud if b.ultima_posicion_id else None,
                'lon': b.ultima_longitud if b.ultima_posicion_id else None,
                'fecha': fields.Datetime.to_string(b.ultima_posicion_fecha) if b.ultima_posicion_id else False,
                'velocidad': b.ultima_velocidad_kmh if b.ultima_posicion_id else None,
                'viajes_periodo': len(viajes_periodo.filtered(lambda v, bid=b.id: v.vehicle_id.id == bid
                                                              and v.resultado in ESTADOS_EVALUADOS)),
                'viaje': False,
            }
            if actual:
                visitadas = actual.parada_line_ids.filtered(lambda l: l.estado_parada == 'atendida')
                fila['viaje'] = {
                    'id': actual.id, 'name': actual.name, 'ruta': actual.ruta_id.display_name,
                    'visitadas': len(visitadas), 'total': actual.total_paradas_viaje,
                    'paradas': [l.parada_id.name for l in visitadas.sorted('secuencia')],
                    'retraso': actual.retraso_acumulado_min, 'desviado': actual.desviado,
                    'cumple_horario': actual.paradas_atrasadas == 0 and actual.retraso_acumulado_min <= self.env[
                        'transporte.viaje']._tolerancias()['retraso_min'],
                }
            filas.append(fila)
        return filas

    @api.model
    def _por_periodo(self, evaluados, incidencias, desde, hasta):
        semanal = (hasta - desde).days > 31
        grupos = OrderedDict()
        for v in evaluados.sorted('fecha_viaje'):
            clave = v.fecha_viaje.strftime('S%G-%V') if semanal else fields.Date.to_string(v.fecha_viaje)
            grupos.setdefault(clave, self.env['transporte.viaje'])
            grupos[clave] |= v
        filas = []
        for clave, vs in grupos.items():
            incs = incidencias.filtered(lambda i, ids=set(vs.ids): i.viaje_id.id in ids)
            fila = self._resumen_grupo(vs, incs, 7 if semanal else 1)
            fila['periodo'] = clave
            filas.append(fila)
        return {'agrupacion': 'semana' if semanal else 'día', 'filas': filas}

    # ------------------------------------------------------------------ API pública
    @api.model
    def get_dashboard_data(self, filtros=None):
        inicio = time.perf_counter()
        filtros = filtros or {}
        desde, hasta = self._rango(filtros)
        dias = (hasta - desde).days + 1
        Viaje = self.env['transporte.viaje']
        viajes = Viaje.search(self._dominio_viajes(filtros, desde, hasta))
        evaluados = viajes.filtered(lambda v: v.resultado in ESTADOS_EVALUADOS)
        incidencias = self.env['transporte.incidencia'].search(self._dominio_incidencias(filtros, desde, hasta))

        rutas = []
        for ruta in self.env['transporte.ruta'].search([]):
            vs = evaluados.filtered(lambda v, rid=ruta.id: v.ruta_id.id == rid)
            fila = self._resumen_grupo(vs, incidencias.filtered(lambda i, rid=ruta.id: i.ruta_id.id == rid), dias)
            fila.update({'id': ruta.id, 'codigo': ruta.codigo, 'nombre': ruta.name,
                         'origen': ruta.origen_parada_id.name or '', 'destino': ruta.destino_parada_id.name or '',
                         'distancia_estimada': ruta.distancia_estimada_km, 'tiempo_estimado': ruta.tiempo_estimado_min,
                         'paradas': ruta.total_paradas})
            rutas.append(fila)

        historial = [{
            'id': v.id, 'name': v.name, 'ruta': v.ruta_id.codigo, 'bus': v.vehicle_id.license_plate or v.vehicle_id.name,
            'salida': fields.Datetime.to_string(v.hora_salida_planificada), 'resultado': v.resultado,
            'puntual': v.puntual, 'retraso_llegada': v.retraso_llegada_min, 'paradas': '%s/%s' % (
                v.paradas_atendidas, v.total_paradas_viaje), 'distancia': v.distancia_recorrida_km,
            'incidencias': v.incidencia_count, 'simulado': v.simulado, 'escenario': v.escenario_simulado or '',
        } for v in evaluados.sorted(lambda x: x.hora_salida_planificada, reverse=True)[:20]]

        datos = {
            'filtros': {'fecha_desde': fields.Date.to_string(desde), 'fecha_hasta': fields.Date.to_string(hasta),
                        'ruta_id': filtros.get('ruta_id') or False, 'vehicle_id': filtros.get('vehicle_id') or False,
                        'datos': filtros.get('datos') or 'todos'},
            'opciones': {
                'rutas': [{'id': r.id, 'nombre': '%s - %s' % (r.codigo, r.name)} for r in self.env['transporte.ruta'].search([])],
                'buses': [{'id': b.id, 'nombre': b.display_name}
                          for b in self.env['fleet.vehicle'].search([('es_bus_pasajeros', '=', True)])],
            },
            'resumen': {
                'viajes': len(viajes), 'evaluados': len(evaluados),
                'en_curso': len(viajes.filtered(lambda v: v.state == 'in_progress')),
                'simulados': len(evaluados.filtered('simulado')), 'reales': len(evaluados.filtered(lambda v: not v.simulado)),
                'cumplen': len(evaluados.filtered(lambda v: v.resultado == 'cumple')),
                'dias': dias,
            },
            'tolerancias': Viaje._tolerancias(),
            'transporte': self._kpis_transporte(evaluados, incidencias, dias),
            'software': self._kpis_software(filtros, desde, hasta, viajes),
            'rutas': rutas,
            'periodos': self._por_periodo(evaluados, incidencias, desde, hasta),
            'vehiculos': self._vehiculos(viajes),
            'historial': historial,
        }
        ms = int((time.perf_counter() - inicio) * 1000)
        datos['calculo_ms'] = ms
        if filtros.get('registrar'):
            self.env['transporte.calidad.medicion'].registrar(
                'dashboard', ms, registros=len(viajes) + len(incidencias),
                detalle='Filtros: %s' % datos['filtros'])
        return datos

    # ------------------------------------------------------------------ exactitud Traccar <-> Odoo
    @api.model
    def verificar_exactitud_sync(self, muestra=50, client=None):
        """Compara las últimas posiciones REALES guardadas en Odoo contra Traccar (misma id de posición).

        Exactitud (%) = posiciones idénticas (lat/lon a 1e-6, fecha y velocidad) / posiciones verificadas × 100.
        """
        inicio = time.perf_counter()
        Pos = self.env['transporte.gps.posicion'].sudo()
        Bus = self.env['fleet.vehicle'].sudo()
        client = client or Bus._traccar_client()
        verificadas, iguales, faltantes, distintas = 0, 0, 0, []
        for bus in Bus.search([('traccar_device_id', '>', 0)]):
            locales = Pos.search([('vehicle_id', '=', bus.id), ('simulado', '=', False)],
                                 order='fecha_gps desc', limit=muestra)
            if not locales:
                continue
            desde = min(locales.mapped('fecha_gps')) - timedelta(seconds=1)
            hasta = max(locales.mapped('fecha_gps')) + timedelta(seconds=1)
            remotas = {}
            for raw in client.get_positions(bus.traccar_device_id, traccar_parser.formato_fecha_api(desde),
                                            traccar_parser.formato_fecha_api(hasta)):
                try:
                    p = traccar_parser.parse_posicion(raw)
                    remotas[p['traccar_position_id']] = p
                except (ValueError, TypeError):
                    continue
            for loc in locales:
                verificadas += 1
                rem = remotas.get(loc.traccar_position_id)
                if not rem:
                    faltantes += 1
                    continue
                if (abs(rem['latitud'] - loc.latitud) < 1e-6 and abs(rem['longitud'] - loc.longitud) < 1e-6
                        and rem['fecha_gps'] == loc.fecha_gps
                        and abs(rem['velocidad_kmh'] - loc.velocidad_kmh) < 0.01):
                    iguales += 1
                else:
                    distintas.append(loc.traccar_position_id)
        if not verificadas:
            raise UserError(_('No hay posiciones reales de Traccar para verificar.'))
        valor = reglas.porcentaje(iguales, verificadas)
        detalle = _('%s verificadas, %s idénticas, %s no encontradas en Traccar, %s con diferencias %s') % (
            verificadas, iguales, faltantes, len(distintas), distintas[:20] or '')
        self.env['transporte.calidad.medicion'].registrar(
            'exactitud_sync', (time.perf_counter() - inicio) * 1000, registros=verificadas, valor=valor,
            ok=valor == 100.0, detalle=detalle)
        return {'valor': valor, 'verificadas': verificadas, 'iguales': iguales, 'faltantes': faltantes,
                'distintas': len(distintas)}

    @api.model
    def action_verificar_exactitud(self):
        try:
            res = self.verificar_exactitud_sync()
        except TraccarError as exc:
            raise UserError(_('No se pudo consultar Traccar: %s') % exc)
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': _('Exactitud Traccar ↔ Odoo'), 'type': 'success' if res['valor'] == 100 else 'warning',
                       'sticky': True,
                       'message': _('%(valor)s %% de %(verificadas)s posiciones idénticas '
                                    '(%(faltantes)s no encontradas, %(distintas)s distintas).') % res},
        }
