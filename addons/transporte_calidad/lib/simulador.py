# -*- coding: utf-8 -*-
"""Generador determinista de recorridos GPS SIMULADOS para escenarios de prueba (A5).

El enunciado permite datos simulados cuando un escenario no puede reproducirse físicamente,
siempre identificados como tales: todo lo que se genere aquí se guarda con `simulado=True`.
Cada escenario declara las incidencias que la lógica de detección DEBERÍA encontrar, lo que
permite medir el "% de detección correcta de incidencias" (métrica de calidad del software).
"""
import math
import random
from datetime import timedelta

M_POR_GRADO = 111320.0

# escenario -> (descripción, incidencias esperadas)
ESCENARIOS = {
    'puntual': ('Recorrido normal dentro de tolerancias', set()),
    'atrasado': ('Salida 10 min tarde: todo el recorrido desplazado',
                 {'retraso_inicio', 'retraso_parada', 'retraso_llegada'}),
    'congestion': ('Salida puntual, tráfico lento (×1.5 en todos los tramos)',
                   {'retraso_parada', 'retraso_llegada', 'diferencia_tiempo'}),
    'parada_omitida': ('El bus no entra a la parada intermedia (pasa a 110 m)', {'parada_omitida'}),
    'desviacion': ('Desvío de hasta 450 m fuera del corredor entre la 2.ª y 3.ª parada', {'desviacion_ruta'}),
    'incompleto': ('El recorrido termina a mitad de ruta', {'recorrido_incompleto', 'parada_omitida'}),
    'perdida_senal': ('El teléfono deja de reportar 5 min en mitad de un tramo', {'perdida_senal'}),
    'muestreo_disperso': ('Recorrido puntual reportado cada 120 s (Traccar Client con intervalo largo)', set()),
}

# Plan de 10 recorridos: (escenario, índice de ruta, índice de bus, hora local de salida, intervalo s)
PLAN_DIEZ = [
    ('puntual', 0, 0, (6, 30), 15),
    ('puntual', 1, 1, (6, 30), 15),
    ('puntual', 2, 0, (8, 0), 15),
    ('atrasado', 0, 1, (8, 0), 15),
    ('congestion', 1, 0, (10, 0), 15),
    ('parada_omitida', 2, 1, (10, 0), 15),
    ('desviacion', 0, 0, (12, 0), 15),
    ('incompleto', 1, 1, (12, 0), 15),
    ('perdida_senal', 2, 0, (14, 0), 15),
    ('muestreo_disperso', 0, 1, (14, 0), 120),
]


def _desplazar(lat, lon, norte_m, este_m):
    return (lat + norte_m / M_POR_GRADO,
            lon + este_m / (M_POR_GRADO * math.cos(math.radians(lat))))


def _perpendicular(a, b):
    """Vector unitario (norte, este) perpendicular al tramo a→b."""
    dn = (b[0] - a[0]) * M_POR_GRADO
    de = (b[1] - a[1]) * M_POR_GRADO * math.cos(math.radians(a[0]))
    largo = math.hypot(dn, de) or 1.0
    return -de / largo, dn / largo


def _unitario(desde, hasta):
    dn = (hasta[0] - desde[0]) * M_POR_GRADO
    de = (hasta[1] - desde[1]) * M_POR_GRADO * math.cos(math.radians(desde[0]))
    largo = math.hypot(dn, de) or 1.0
    return dn / largo, de / largo


def _hacia_vecinos(previa, parada, siguiente):
    """Dirección (norte, este) de la bisectriz interna del ángulo previa-parada-siguiente.

    Un atajo en esa dirección hace que ningún tramo del recorrido se acerque a la parada; si las
    tres paradas son casi colineales se usa la perpendicular al tramo.
    """
    a, b = _unitario(parada, previa), _unitario(parada, siguiente)
    sn, se = a[0] + b[0], a[1] + b[1]
    largo = math.hypot(sn, se)
    if largo < 0.2:
        return _perpendicular(previa, siguiente)
    return sn / largo, se / largo


def _interpolar(a, b, f):
    return a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f


def generar_recorrido(paradas, salida_plan, escenario, intervalo_s=15, semilla=0):
    """Genera la traza GPS de un recorrido.

    :param paradas: [{'lat', 'lon', 't_min'}] en orden de secuencia (t_min = minutos desde el origen)
    :param salida_plan: datetime UTC de salida programada
    :return: dict(salida_real, llegada_real, puntos=[(fecha, lat, lon, vel_kmh)], esperadas, descripcion)
    """
    if escenario not in ESCENARIOS:
        raise ValueError('Escenario desconocido: %s' % escenario)
    if len(paradas) < 3:
        raise ValueError('Se necesitan al menos 3 paradas para simular un recorrido')
    rnd = random.Random(semilla)
    descripcion, esperadas = ESCENARIOS[escenario]
    factor = 1.5 if escenario == 'congestion' else 1.0
    retraso_salida = {'atrasado': 10.0, 'puntual': 1.0, 'muestreo_disperso': 1.0}.get(escenario, 0.0)
    salida_real = salida_plan + timedelta(minutes=retraso_salida)

    nodos = [(p['lat'], p['lon']) for p in paradas]
    tiempos = [p['t_min'] * factor for p in paradas]
    ultima = len(nodos) - 1
    if escenario == 'incompleto':
        ultima = len(nodos) // 2 - 1
    medio = len(nodos) // 2
    if escenario == 'parada_omitida':
        pn, pe = _hacia_vecinos(nodos[medio - 1], nodos[medio], nodos[medio + 1])
        nodos[medio] = _desplazar(nodos[medio][0], nodos[medio][1], pn * 110, pe * 110)

    def posicion(t_min):
        """Posición sobre la ruta en el minuto t (desde la salida real)."""
        for i in range(ultima):
            if tiempos[i] <= t_min <= tiempos[i + 1]:
                tramo = tiempos[i + 1] - tiempos[i] or 1.0
                f = (t_min - tiempos[i]) / tramo
                lat, lon = _interpolar(nodos[i], nodos[i + 1], f)
                if escenario == 'desviacion' and i == 1:
                    pn, pe = _perpendicular(nodos[1], nodos[2])
                    desvio = 450.0 * math.sin(math.pi * f)
                    lat, lon = _desplazar(lat, lon, pn * desvio, pe * desvio)
                return lat, lon
        return nodos[ultima]

    # hueco de señal: 5 min centrados en el tramo más largo
    hueco = None
    if escenario == 'perdida_senal':
        i = max(range(ultima), key=lambda k: tiempos[k + 1] - tiempos[k])
        centro = (tiempos[i] + tiempos[i + 1]) / 2.0
        hueco = (centro - 2.5, centro + 2.5)

    fin_min = tiempos[ultima]
    puntos, t, previo = [], 0.0, None
    paso = intervalo_s / 60.0
    while True:
        t_actual = min(t, fin_min)
        if not (hueco and hueco[0] < t_actual < hueco[1]):
            lat, lon = posicion(t_actual)
            # ruido GPS de ±3 m (determinista por semilla)
            lat, lon = _desplazar(lat, lon, rnd.uniform(-3, 3), rnd.uniform(-3, 3))
            vel = 0.0
            if previo:
                d = math.hypot((lat - previo[1]) * M_POR_GRADO,
                               (lon - previo[2]) * M_POR_GRADO * math.cos(math.radians(lat)))
                dt = (t_actual - previo[0]) * 60.0
                vel = round(d / dt * 3.6, 1) if dt else 0.0
            fecha = salida_real + timedelta(minutes=t_actual)
            puntos.append((fecha.replace(microsecond=0), round(lat, 6), round(lon, 6), vel))
            previo = (t_actual, lat, lon)
        if t_actual >= fin_min:
            break
        t += paso

    llegada_real = salida_real + timedelta(minutes=fin_min + (2 if escenario == 'incompleto' else 0))
    return {
        'salida_real': salida_real.replace(microsecond=0),
        'llegada_real': llegada_real.replace(microsecond=0),
        'puntos': puntos,
        'esperadas': set(esperadas),
        'descripcion': descripcion,
    }
