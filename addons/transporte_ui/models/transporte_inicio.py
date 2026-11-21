# -*- coding: utf-8 -*-
"""Datos de la pantalla de Inicio. Todo se calcula en vivo reutilizando el dashboard de calidad."""
from datetime import timedelta

from odoo import api, fields, models

DIAS_RESUMEN = 7

# Accesos que se muestran como tarjetas en Inicio; los demás siguen disponibles en el menú superior.
PRINCIPALES = ('en_vivo', 'dashboard', 'mapa_rutas', 'viajes', 'incidencias', 'rutas')

# (clave, menú que controla la visibilidad, acción, título, descripción, icono FontAwesome, tono)
ACCESOS = [
    ('en_vivo', 'transporte_ui.menu_en_vivo', 'transporte_ui.action_en_vivo',
     'En vivo', 'Líneas, buses en el mapa y llegadas estimadas', 'fa-location-arrow', 'verde'),
    ('dashboard', 'transporte_calidad.menu_calidad_dashboard', 'transporte_calidad.action_dashboard_calidad',
     'Dashboard de calidad', 'Indicadores, comparación por ruta y período, historial', 'fa-tachometer', 'azul'),
    ('mapa_buses', 'transporte_gps_traccar.menu_gps_map', 'transporte_gps_traccar.action_gps_map',
     'Mapa GPS', 'Última posición GPS de cada bus', 'fa-map-marker', 'turquesa'),
    ('mapa_rutas', 'transporte_calidad.menu_calidad_mapa_rutas', 'transporte_calidad.action_mapa_rutas',
     'Mapa de rutas', 'Trazados, paradas y cumplimiento por ruta', 'fa-map', 'turquesa'),
    ('viajes', 'transporte_core.menu_transporte_viaje', 'transporte_core.action_transporte_viaje',
     'Viajes', 'Programar, despachar y seguir recorridos', 'fa-road', 'ambar'),
    ('incidencias', 'transporte_calidad.menu_calidad_incidencias', 'transporte_calidad.action_incidencia',
     'Incidencias', 'Retrasos, desvíos, paradas omitidas, señal', 'fa-exclamation-triangle', 'rojo'),
    ('rutas', 'transporte_core.menu_transporte_ruta', 'transporte_core.action_transporte_ruta',
     'Rutas', 'Origen, destino, horarios y corredor', 'fa-code-fork', 'violeta'),
    ('paradas', 'transporte_core.menu_transporte_parada', 'transporte_core.action_transporte_parada',
     'Paradas', 'Puntos de control y radio de detección', 'fa-map-pin', 'azul'),
    ('buses', 'transporte_core.menu_transporte_bus', 'transporte_core.action_transporte_bus',
     'Buses', 'Flota, capacidad y dispositivo GPS', 'fa-bus', 'verde'),
    ('conductores', 'transporte_core.menu_transporte_conductor', 'transporte_core.action_transporte_conductor',
     'Conductores', 'Licencias y habilitación', 'fa-id-card', 'turquesa'),
    ('analisis', 'transporte_calidad.menu_calidad_analisis', 'transporte_calidad.action_analisis_viajes',
     'Análisis', 'Pivot y gráficos de recorridos', 'fa-bar-chart', 'ambar'),
    ('software', 'transporte_calidad.menu_calidad_mediciones', 'transporte_calidad.action_medicion',
     'Calidad del software', 'Tiempos de respuesta y exactitud', 'fa-check-square-o', 'violeta'),
    ('simulacion', 'transporte_calidad.menu_calidad_simulacion', 'transporte_calidad.action_simulacion',
     'Recorridos simulados', 'Escenarios de prueba (marcados SIMULADO)', 'fa-flask', 'gris'),
]


class TransporteInicio(models.AbstractModel):
    _name = 'transporte.inicio'
    _description = 'Pantalla de inicio de SGM-TB'

    @api.model
    def _saludo(self):
        hora = fields.Datetime.context_timestamp(self, fields.Datetime.now()).hour
        if hora < 12:
            return 'Buenos días'
        return 'Buenas tardes' if hora < 19 else 'Buenas noches'

    @api.model
    def _accesos(self):
        visibles = self.env['ir.ui.menu']._visible_menu_ids()
        filas = []
        for clave, menu_xmlid, accion, titulo, descripcion, icono, tono in ACCESOS:
            menu = self.env.ref(menu_xmlid, raise_if_not_found=False)
            if menu and menu.id in visibles:
                filas.append({'clave': clave, 'accion': accion, 'menu_id': menu.id, 'titulo': titulo,
                              'descripcion': descripcion, 'icono': icono, 'tono': tono,
                              'principal': clave in PRINCIPALES})
        return filas

    @api.model
    def get_inicio_data(self):
        hoy = fields.Date.context_today(self)
        desde = hoy - timedelta(days=DIAS_RESUMEN - 1)
        d = self.env['transporte.calidad.dashboard'].get_dashboard_data(
            {'fecha_desde': fields.Date.to_string(desde), 'fecha_hasta': fields.Date.to_string(hoy)})
        t, s = d['transporte'], d['software']

        Viaje = self.env['transporte.viaje']
        hoy_por_estado = {g['state']: g['state_count'] for g in Viaje.read_group(
            [('fecha_viaje', '=', hoy)], ['state'], ['state'])}
        abiertas = self.env['transporte.incidencia'].search_count([('estado', 'in', ('abierta', 'en_atencion'))])

        vehiculos = d['vehiculos']
        en_ruta = [v for v in vehiculos if v['viaje']]
        return {
            'usuario': self.env.user.name,
            'saludo': self._saludo(),
            'hoy': fields.Date.to_string(hoy),
            'periodo': {'desde': fields.Date.to_string(desde), 'hasta': fields.Date.to_string(hoy),
                        'dias': DIAS_RESUMEN},
            'kpis': {
                'en_ruta': len(en_ruta),
                'buses': len(vehiculos),
                'con_senal': len([v for v in vehiculos if v['senal'] == 'con_senal']),
                'viajes_hoy': sum(hoy_por_estado.values()),
                'completados_hoy': hoy_por_estado.get('completed', 0),
                'programados_hoy': hoy_por_estado.get('scheduled', 0),
                'cumplimiento': t['cumplimiento_rutas']['valor'],
                'puntualidad': t['puntualidad_paradas']['valor'],
                'retraso_promedio': t['retraso_promedio']['valor'],
                'incidencias_periodo': t['incidencias']['valor'],
                'incidencias_abiertas': abiertas,
                'integridad_gps': s['integridad_gps']['valor'],
                'deteccion_correcta': s['deteccion_correcta']['valor'],
            },
            'evaluados': d['resumen']['evaluados'],
            'simulados': d['resumen']['simulados'],
            'en_ruta': [{
                'bus': v['nombre'], 'placa': v['placa'], 'senal': v['senal'],
                'viaje_id': v['viaje']['id'], 'viaje': v['viaje']['name'], 'ruta': v['viaje']['ruta'],
                'visitadas': v['viaje']['visitadas'], 'total': v['viaje']['total'],
                'retraso': v['viaje']['retraso'], 'desviado': v['viaje']['desviado'],
                'cumple_horario': v['viaje']['cumple_horario'],
            } for v in en_ruta],
            'top_incidencias': t['incidencias']['por_tipo'][:4],
            'accesos': self._accesos(),
        }
