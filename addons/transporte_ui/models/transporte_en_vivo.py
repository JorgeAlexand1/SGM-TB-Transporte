# -*- coding: utf-8 -*-
"""Datos de la pantalla «En vivo» (inspirada en apps de transporte público como Moovit).

Cada ruta se muestra como una *línea* con su color; para cada bus en ruta se calcula en qué tramo
va, la próxima parada y la hora estimada de llegada (hora programada + retraso acumulado actual).
La confianza de la estimación depende de la señal GPS del bus, igual que el semáforo de precisión
de Moovit: GPS en vivo (alta), señal desactualizada (media) o solo horario (baja).
"""
from datetime import timedelta

from odoo import api, fields, models

# Colores de línea: contrastan entre sí y con el fondo claro del mapa.
COLORES_LINEA = ['#E8553D', '#1E88E5', '#2EAD6B', '#8E5BD6', '#F2A516', '#13A3A0', '#D6407E', '#5C6B7A']

CONFIANZA = {'con_senal': 'alta', 'sin_senal': 'media'}
HORAS_PROXIMAS_SALIDAS = 12


class TransporteEnVivo(models.AbstractModel):
    _name = 'transporte.en.vivo'
    _description = 'Pantalla En vivo de SGM-TB'

    @staticmethod
    def _iso(valor):
        return fields.Datetime.to_string(valor) if valor else False

    @staticmethod
    def _minutos(desde, hasta):
        return round((hasta - desde).total_seconds() / 60.0, 1)

    @api.model
    def _paradas_viaje(self, viaje):
        """Estado de cada parada del viaje y llegada estimada a las pendientes.

        Devuelve las filas y el índice de la última parada ya pasada (atendida u omitida; -1 si ninguna).
        """
        retraso = max(viaje.retraso_acumulado_min or 0.0, 0.0)
        filas, ultima_pasada = [], -1
        for i, linea in enumerate(viaje.parada_line_ids.sorted('secuencia')):
            fila = {'secuencia': linea.secuencia, 'nombre': linea.parada_id.name, 'estado': linea.estado_parada,
                    'programada': self._iso(linea.hora_planificada), 'real': self._iso(linea.hora_llegada_real),
                    'eta': False, 'retraso': None}
            if linea.estado_parada == 'atendida' and linea.hora_llegada_real and linea.hora_planificada:
                fila['retraso'] = self._minutos(linea.hora_planificada, linea.hora_llegada_real)
            if linea.estado_parada != 'pendiente':
                ultima_pasada = i
            elif linea.hora_planificada:
                fila['eta'] = self._iso(linea.hora_planificada + timedelta(minutes=retraso))
            filas.append(fila)
        return filas, ultima_pasada

    @api.model
    def _bus_en_ruta(self, viaje, tolerancia):
        bus = viaje.vehicle_id
        paradas, ultima_pasada = self._paradas_viaje(viaje)
        proxima = next((p for p in paradas[ultima_pasada + 1:] if p['estado'] == 'pendiente'), None)
        con_gps = bool(bus.ultima_posicion_id)
        retraso = viaje.retraso_acumulado_min or 0.0
        if viaje.desviado:
            estado = 'desviado'
        elif retraso > tolerancia:
            estado = 'retraso'
        else:
            estado = 'a_tiempo'
        return {
            'viaje_id': viaje.id, 'viaje': viaje.name, 'bus_id': bus.id,
            'bus': bus.license_plate or bus.name, 'nombre_bus': bus.display_name,
            'confianza': CONFIANZA.get(bus.estado_senal, 'baja'), 'senal': bus.estado_senal,
            'lat': bus.ultima_latitud if con_gps else None, 'lon': bus.ultima_longitud if con_gps else None,
            'velocidad': bus.ultima_velocidad_kmh if con_gps else None,
            'fecha_gps': self._iso(bus.ultima_posicion_fecha) if con_gps else False,
            'retraso': retraso, 'estado': estado, 'simulado': viaje.simulado,
            'paradas': paradas, 'tramo': ultima_pasada, 'proxima': proxima,
            'visitadas': len([p for p in paradas if p['estado'] == 'atendida']),
        }

    @api.model
    def get_en_vivo(self):
        ahora = fields.Datetime.now()
        tolerancia = self.env['transporte.viaje']._tolerancias()['retraso_min']
        Viaje = self.env['transporte.viaje']
        en_ruta = Viaje.search([('state', '=', 'in_progress')], order='hora_salida_planificada')
        programados = Viaje.search([
            ('state', '=', 'scheduled'),
            ('hora_salida_planificada', '>=', ahora - timedelta(minutes=30)),
            ('hora_salida_planificada', '<=', ahora + timedelta(hours=HORAS_PROXIMAS_SALIDAS)),
        ], order='hora_salida_planificada')

        lineas = []
        for i, ruta in enumerate(self.env['transporte.ruta'].search([], order='codigo, id')):
            lineas.append({
                'id': ruta.id, 'codigo': ruta.codigo, 'nombre': ruta.name,
                'color': COLORES_LINEA[i % len(COLORES_LINEA)],
                'origen': ruta.origen_parada_id.name or '', 'destino': ruta.destino_parada_id.name or '',
                'tiempo': ruta.tiempo_estimado_min, 'distancia': ruta.distancia_estimada_km,
                'trazado': [list(p) for p in ruta._trazado_evaluacion()],
                'paradas': [{'secuencia': l.secuencia, 'nombre': l.parada_id.name, 'lat': l.parada_id.latitude,
                             'lon': l.parada_id.longitude, 'min': l.tiempo_desde_origen_min}
                            for l in ruta.parada_ids.sorted('secuencia')],
                'buses': [self._bus_en_ruta(v, tolerancia) for v in en_ruta if v.ruta_id == ruta],
                'salidas': [{'viaje_id': v.id, 'bus': v.vehicle_id.license_plate or v.vehicle_id.name,
                             'hora': self._iso(v.hora_salida_planificada)}
                            for v in programados if v.ruta_id == ruta][:3],
                'cumplimiento': round(ruta.cumplimiento_pct, 1), 'evaluados': ruta.viajes_evaluados,
            })
        return {
            'ahora': self._iso(ahora),
            'tolerancia': tolerancia,
            'lineas': lineas,
            'total_buses': sum(len(l['buses']) for l in lineas),
        }
