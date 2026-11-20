#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Medición ANTES / DESPUÉS de la mejora de geocercas (Actividad 10 - PDCA).

Problema: con intervalos de reporte largos de Traccar Client el bus puede pasar por una parada
entre dos muestras GPS y el sistema la registra como "omitida" aunque fue visitada.

Para cada intervalo de reporte y cada ruta se simulan N recorridos PUNTUALES (sin incidencias
reales) y se cuentan las paradas mal detectadas con la geocerca por punto (antes) y por tramo
(después). Usa la misma lógica que el sistema (lib/ de los módulos), sin Odoo.

Uso:
    python3 scripts/medir_deteccion_paradas.py [--repeticiones 20] [--velocidad-kmh 20] [--csv salida.csv]
"""
import argparse
import csv
import os
import sys
from datetime import datetime, timedelta

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'addons'))
sys.path[:0] = [os.path.join(RAIZ, 'transporte_gps_traccar', 'lib'), os.path.join(RAIZ, 'transporte_calidad', 'lib')]

import geo_utils  # noqa: E402
import reglas  # noqa: E402
import simulador  # noqa: E402

# Rutas DEMO de Ambato (coordenadas, radio de detección y minutos desde el origen)
RUTAS = {
    'DEMO-RUT-01': [(-1.2384, -78.6215, 35, 0), (-1.2423, -78.6254, 30, 8), (-1.2471, -78.6298, 40, 16),
                    (-1.2515, -78.6332, 30, 23), (-1.2560, -78.6375, 35, 30), (-1.2612, -78.6410, 45, 38),
                    (-1.2685, -78.6470, 50, 45)],
    'DEMO-RUT-02': [(-1.2440, -78.6120, 40, 0), (-1.2505, -78.6185, 35, 7), (-1.2471, -78.6298, 40, 15),
                    (-1.2560, -78.6375, 35, 22), (-1.2580, -78.6240, 30, 29), (-1.2685, -78.6470, 50, 35)],
    'DEMO-RUT-03': [(-1.2330, -78.6280, 40, 0), (-1.2384, -78.6215, 35, 9), (-1.2505, -78.6185, 35, 20),
                    (-1.2612, -78.6410, 45, 31), (-1.2720, -78.6520, 50, 40)],
}
INTERVALOS = [10, 15, 30, 60, 90, 120, 180, 300]  # 300 s = valor por defecto de Traccar Client


def tiempos_por_velocidad(ruta, velocidad_kmh):
    """Minutos desde el origen recorriendo los tramos a velocidad constante (el bus no se detiene)."""
    t, tiempos = 0.0, [0.0]
    for (la1, lo1, _r1, _t1), (la2, lo2, _r2, _t2) in zip(ruta, ruta[1:]):
        t += geo_utils.haversine_m(la1, lo1, la2, lo2) / 1000.0 / velocidad_kmh * 60.0
        tiempos.append(t)
    return tiempos


def medir(repeticiones, velocidad_kmh):
    t0 = datetime(2026, 11, 19, 13, 0)
    filas = []
    for intervalo in INTERVALOS:
        for modo in ('punto', 'segmento'):
            paradas_total = paradas_fallidas = viajes = viajes_falsos = 0
            for codigo, ruta in RUTAS.items():
                tiempos = tiempos_por_velocidad(ruta, velocidad_kmh)
                defs = [{'lat': la, 'lon': lo, 't_min': t} for (la, lo, _r, _t), t in zip(ruta, tiempos)]
                geo = [{'lat': la, 'lon': lo, 'radio': r} for la, lo, r, _t in ruta]
                for semilla in range(repeticiones):
                    # desfase aleatorio del primer reporte respecto a la salida
                    salida = t0 + timedelta(seconds=semilla * 7 % intervalo)
                    sim = simulador.generar_recorrido(defs, salida, 'puntual', intervalo, semilla)
                    puntos = [(f, la, lo) for f, la, lo, _v in sim['puntos']]
                    llegadas = reglas.detectar_paradas(puntos, geo, modo)
                    fallidas = sum(1 for ll in llegadas if ll is None)
                    paradas_total += len(geo)
                    paradas_fallidas += fallidas
                    viajes += 1
                    viajes_falsos += 1 if fallidas else 0
            filas.append({
                'intervalo_s': intervalo, 'modo': modo, 'viajes': viajes, 'paradas': paradas_total,
                'paradas_no_detectadas': paradas_fallidas,
                'deteccion_paradas_pct': reglas.porcentaje(paradas_total - paradas_fallidas, paradas_total),
                'viajes_con_falsa_omision_pct': reglas.porcentaje(viajes_falsos, viajes),
            })
    return filas


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--repeticiones', type=int, default=20, help='recorridos por ruta e intervalo')
    ap.add_argument('--velocidad-kmh', type=float, default=20.0,
                    help='velocidad constante del bus (20 km/h ≈ promedio urbano; sin detenerse en paradas)')
    ap.add_argument('--csv', help='ruta del CSV de salida')
    args = ap.parse_args()
    filas = medir(args.repeticiones, args.velocidad_kmh)
    print('Velocidad simulada: %.0f km/h · %d recorridos por ruta e intervalo\n' % (
        args.velocidad_kmh, args.repeticiones))
    print('| Intervalo (s) | Modo | Viajes | Paradas | No detectadas | Detección (%) | Viajes con falsa omisión (%) |')
    print('|---:|:---|---:|---:|---:|---:|---:|')
    for f in filas:
        print('| %(intervalo_s)s | %(modo)s | %(viajes)s | %(paradas)s | %(paradas_no_detectadas)s | '
              '%(deteccion_paradas_pct)s | %(viajes_con_falsa_omision_pct)s |' % f)
    if args.csv:
        with open(args.csv, 'w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=list(filas[0]))
            w.writeheader()
            w.writerows(filas)
        print('\nCSV: %s' % args.csv)


if __name__ == '__main__':
    main()
