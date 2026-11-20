#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba de rendimiento extremo a extremo (A9) contra un Odoo en ejecución, vía JSON-RPC.

Mide el tiempo de respuesta (incluye red + servidor + BD) al consultar recorridos, mapas y
métricas con distintas cantidades de registros, y guarda cada medición en Odoo
(modelo transporte.calidad.medicion, tipo "prueba_rendimiento") para el indicador de tiempo de respuesta.

Uso (las credenciales NUNCA se escriben en el repositorio):
    ODOO_URL=http://localhost:8070 ODOO_DB=transporte_universitario_gc ODOO_USER=admin \
    ODOO_PASSWORD=*** python3 scripts/prueba_rendimiento.py [--repeticiones 5] [--csv salida.csv]
"""
import argparse
import csv
import json
import os
import statistics
import sys
import time
import urllib.request
from datetime import date, timedelta

UMBRAL_MS = 3000  # RNF-03


def _jsonrpc(url, servicio, metodo, *args):
    cuerpo = json.dumps({'jsonrpc': '2.0', 'method': 'call', 'id': 1,
                         'params': {'service': servicio, 'method': metodo, 'args': list(args)}}).encode()
    peticion = urllib.request.Request(url + '/jsonrpc', data=cuerpo, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(peticion, timeout=120) as resp:
        datos = json.loads(resp.read())
    if datos.get('error'):
        raise RuntimeError(datos['error'].get('data', {}).get('message') or datos['error'])
    return datos['result']


def conectar():
    """JSON-RPC (mismo canal que el cliente web; admite valores nulos = 'no aplica')."""
    url = os.environ.get('ODOO_URL', 'http://localhost:8070').rstrip('/')
    db = os.environ.get('ODOO_DB', 'transporte_universitario_gc')
    usuario = os.environ.get('ODOO_USER', 'admin')
    clave = os.environ.get('ODOO_PASSWORD')
    if not clave:
        sys.exit('Defina ODOO_PASSWORD en el entorno.')
    uid = _jsonrpc(url, 'common', 'authenticate', db, usuario, clave, {})
    if not uid:
        sys.exit('Autenticación rechazada.')

    def call(modelo, metodo, *args, **kw):
        return _jsonrpc(url, 'object', 'execute_kw', db, uid, clave, modelo, metodo, list(args), kw)
    return call


def medir(call, nombre, registros, repeticiones, funcion):
    tiempos = []
    for _ in range(repeticiones):
        inicio = time.perf_counter()
        funcion()
        tiempos.append((time.perf_counter() - inicio) * 1000)
    fila = {'operacion': nombre, 'registros': registros, 'repeticiones': repeticiones,
            'promedio_ms': round(statistics.mean(tiempos), 1), 'max_ms': round(max(tiempos), 1),
            'cumple_umbral': max(tiempos) < UMBRAL_MS}
    call('transporte.calidad.medicion', 'registrar', 'prueba_rendimiento', fila['promedio_ms'], registros,
         0.0, fila['cumple_umbral'], 'script %s (max %s ms)' % (nombre, fila['max_ms']))
    print('%-34s registros=%-7s prom=%8.1f ms  max=%8.1f ms  %s' % (
        nombre, registros, fila['promedio_ms'], fila['max_ms'], 'OK' if fila['cumple_umbral'] else 'LENTO'))
    return fila


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--repeticiones', type=int, default=5)
    ap.add_argument('--csv')
    args = ap.parse_args()
    call = conectar()
    r = args.repeticiones
    filas = []
    total_viajes = call('transporte.viaje', 'search_count', [])
    campos = ['name', 'ruta_id', 'vehicle_id', 'hora_salida_planificada', 'resultado', 'retraso_llegada_min',
              'distancia_recorrida_km', 'incidencia_count']
    for limite in (10, 100, 1000):
        n = min(limite, total_viajes)
        filas.append(medir(call, 'consulta_recorridos_%s' % limite, n, r,
                           lambda lim=limite: call('transporte.viaje', 'search_read', [], fields=campos, limit=lim)))

    viajes = call('transporte.viaje', 'search_read', [('cantidad_posiciones', '>', 0)],
                  fields=['cantidad_posiciones'], order='cantidad_posiciones desc', limit=1)
    filas.append(medir(call, 'mapa_buses', call('fleet.vehicle', 'search_count', [('traccar_device_id', '>', 0)]), r,
                       lambda: call('fleet.vehicle', 'get_datos_mapa', False)))
    if viajes:
        v = viajes[0]
        filas.append(medir(call, 'mapa_viaje_trazado', v['cantidad_posiciones'], r,
                           lambda: call('fleet.vehicle', 'get_datos_mapa', v['id'])))

    hoy = date.today()
    for dias in (1, 7, 30, 90):
        filtros = {'fecha_desde': str(hoy - timedelta(days=dias - 1)), 'fecha_hasta': str(hoy)}
        n = call('transporte.viaje', 'search_count', [('fecha_viaje', '>=', filtros['fecha_desde'])])
        filas.append(medir(call, 'metricas_dashboard_%sd' % dias, n, r,
                           lambda f=filtros: call('transporte.calidad.dashboard', 'get_dashboard_data', f)))

    if args.csv:
        with open(args.csv, 'w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=list(filas[0]))
            w.writeheader()
            w.writerows(filas)
        print('CSV: %s' % args.csv)
    sys.exit(0 if all(f['cumple_umbral'] for f in filas) else 1)


if __name__ == '__main__':
    main()
