# -*- coding: utf-8 -*-
"""Funciones geodésicas y de señal puras (sin dependencias de Odoo) para poder probarlas con pytest."""
import math
from datetime import timedelta

RADIO_TIERRA_M = 6371008.8
KNOTS_A_KMH = 1.852
CERO_GPS = 1e-7  # ~1 cm: tolerancia para reconocer el punto nulo (0, 0) sin comparar floats con ==


def haversine_m(lat1, lon1, lat2, lon2):
    """Distancia ortodrómica en metros entre dos coordenadas WGS84."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * RADIO_TIERRA_M * math.asin(min(1.0, math.sqrt(a)))


def dentro_de_radio(lat, lon, centro_lat, centro_lon, radio_m):
    """True si la posición está a una distancia <= radio_m (límite inclusivo) del centro."""
    return haversine_m(lat, lon, centro_lat, centro_lon) <= radio_m


def coordenadas_validas(lat, lon):
    """Rango WGS84 válido y descarta el punto nulo (0, 0) típico de un GPS sin fix."""
    if lat is None or lon is None:
        return False
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return False
    return not (abs(lat) < CERO_GPS and abs(lon) < CERO_GPS)


def nudos_a_kmh(nudos):
    return round((nudos or 0.0) * KNOTS_A_KMH, 2)


def distancia_total_km(puntos):
    """Suma de tramos consecutivos de una lista ordenada de (lat, lon), en km."""
    total = 0.0
    for (la1, lo1), (la2, lo2) in zip(puntos, puntos[1:]):
        total += haversine_m(la1, lo1, la2, lo2)
    return round(total / 1000.0, 3)


def senal_desactualizada(ultima_fecha, ahora, minutos_max):
    """True si no hay posición o ésta supera `minutos_max` minutos de antigüedad (límite estricto)."""
    if not ultima_fecha:
        return True
    return (ahora - ultima_fecha) > timedelta(minutes=minutos_max)


def proyeccion_en_segmento(lat, lon, a_lat, a_lon, b_lat, b_lon):
    """Distancia (m) del punto P al segmento AB y fracción t∈[0,1] del punto más cercano sobre AB.

    Usa una proyección equirectangular local centrada en P: el error es despreciable para
    tramos urbanos (< 2 km), que es el caso de dos muestras GPS consecutivas o de un corredor de ruta.
    """
    k = math.pi / 180.0 * RADIO_TIERRA_M
    cos0 = math.cos(math.radians(lat))
    ax, ay = (a_lon - lon) * cos0 * k, (a_lat - lat) * k
    bx, by = (b_lon - lon) * cos0 * k, (b_lat - lat) * k
    dx, dy = bx - ax, by - ay
    largo2 = dx * dx + dy * dy
    t = 0.0 if largo2 == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / largo2))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(cx, cy), t


def distancia_punto_segmento_m(lat, lon, a_lat, a_lon, b_lat, b_lon):
    """Distancia mínima en metros del punto (lat, lon) al segmento A-B."""
    return proyeccion_en_segmento(lat, lon, a_lat, a_lon, b_lat, b_lon)[0]


def paso_por_radio(parada_lat, parada_lon, radio_m, previa, actual, modo='segmento'):
    """Decide si el bus pasó por una geocerca circular entre dos muestras GPS.

    :param previa: (lat, lon) de la muestra anterior o None
    :param actual: (lat, lon) de la muestra actual
    :param modo: 'punto' (solo la muestra actual) o 'segmento' (tramo previa→actual)
    :return: (detectada, distancia_m, t) donde t es la fracción del tramo en la que ocurrió el paso
             (1.0 = en la muestra actual)
    """
    dist = haversine_m(actual[0], actual[1], parada_lat, parada_lon)
    if dist <= radio_m:
        return True, dist, 1.0
    if modo != 'segmento' or previa is None:
        return False, dist, 1.0
    d_seg, t = proyeccion_en_segmento(parada_lat, parada_lon, previa[0], previa[1], actual[0], actual[1])
    if d_seg <= radio_m:
        return True, d_seg, t
    return False, dist, 1.0
