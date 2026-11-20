# -*- coding: utf-8 -*-
"""Funciones geodésicas y de señal puras (sin dependencias de Odoo) para poder probarlas con pytest."""
import math
from datetime import timedelta

RADIO_TIERRA_M = 6371008.8
KNOTS_A_KMH = 1.852


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
    return not (lat == 0.0 and lon == 0.0)


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
