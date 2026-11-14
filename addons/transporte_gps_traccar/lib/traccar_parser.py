# -*- coding: utf-8 -*-
"""Normalización de posiciones de Traccar (API REST y forward JSON) a un dict propio."""
from datetime import datetime, timezone

try:  # ejecución dentro de Odoo (paquete) o aislada con pytest
    from .geo_utils import coordenadas_validas, nudos_a_kmh
except ImportError:  # pragma: no cover
    from geo_utils import coordenadas_validas, nudos_a_kmh


def parse_fecha_traccar(texto):
    """ISO 8601 de Traccar -> datetime ingenuo en UTC (formato que usa Odoo)."""
    if not texto:
        raise ValueError("Fecha vacía")
    dt = datetime.fromisoformat(str(texto).replace('Z', '+00:00'))
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def formato_fecha_api(dt):
    """datetime ingenuo UTC -> parámetro `from`/`to` de la API de Traccar."""
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def parse_posicion(raw):
    """Convierte una posición cruda de Traccar. Lanza ValueError si faltan campos obligatorios."""
    if not isinstance(raw, dict):
        raise ValueError("La posición debe ser un objeto JSON")
    for campo in ('id', 'deviceId', 'latitude', 'longitude'):
        if raw.get(campo) is None:
            raise ValueError("Falta el campo obligatorio '%s'" % campo)
    fecha = raw.get('fixTime') or raw.get('deviceTime')
    lat = float(raw['latitude'])
    lon = float(raw['longitude'])
    return {
        'traccar_position_id': int(raw['id']),
        'traccar_device_id': int(raw['deviceId']),
        'latitud': lat,
        'longitud': lon,
        'velocidad_kmh': nudos_a_kmh(float(raw.get('speed') or 0.0)),
        'fecha_gps': parse_fecha_traccar(fecha),
        'valida': bool(raw.get('valid', True)) and coordenadas_validas(lat, lon),
    }


def parse_payload_forward(payload):
    """Acepta {'position': {...}} (forward.json de Traccar) o una posición directa."""
    if isinstance(payload, dict) and isinstance(payload.get('position'), dict):
        return parse_posicion(payload['position'])
    return parse_posicion(payload)
