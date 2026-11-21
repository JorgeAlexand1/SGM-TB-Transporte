# -*- coding: utf-8 -*-
"""Reglas de evaluación de recorridos y fórmulas de indicadores (A6 / A7).

Funciones puras (sin Odoo) para poder verificarlas con pytest como pruebas de caja blanca.
Todas las fechas son `datetime` ingenuos en UTC (convención de Odoo).
"""
import math

try:  # dentro de Odoo
    from odoo.addons.transporte_gps_traccar.lib import geo_utils
except ImportError:  # pytest aislado (conftest añade lib/ del módulo GPS al sys.path)
    import geo_utils

# ---------------------------------------------------------------------------------------------
# Tolerancias por defecto (justificación en docs/METRICAS.md §2)
# ---------------------------------------------------------------------------------------------
TOLERANCIAS_DEFECTO = {
    'retraso_min': 5.0,          # llegada hasta 5 min tarde = puntual (ejemplo del enunciado)
    'adelanto_min': 2.0,         # adelantarse más de 2 min deja pasajeros en la parada
    'ancho_corredor_m': 150.0,   # semiancho del corredor alrededor del trazado de referencia
    'fuera_consecutivas': 3,     # nº mínimo de posiciones seguidas fuera del corredor
    'gap_senal_min': 3.0,        # hueco entre reportes GPS que se considera pérdida de señal
    'duracion_pct': 20.0,        # diferencia tolerada entre duración real y estimada
}

TIPOS_AUTOMATICOS = (
    'retraso_inicio', 'retraso_parada', 'adelanto_parada', 'retraso_llegada', 'parada_omitida',
    'recorrido_incompleto', 'diferencia_tiempo', 'desviacion_ruta', 'perdida_senal',
)

ESTADOS_FINALIZADOS = ('completed', 'cancelled')


# ---------------------------------------------------------------------------------------------
# Utilidades numéricas
# ---------------------------------------------------------------------------------------------
def minutos_entre(desde, hasta):
    """Minutos (con signo, 2 decimales) de `desde` a `hasta`; None si falta alguno."""
    if not desde or not hasta:
        return None
    return round((hasta - desde).total_seconds() / 60.0, 2)


def porcentaje(numerador, denominador):
    """numerador / denominador × 100 con 2 decimales; None si el denominador es 0 (indicador no aplicable)."""
    if not denominador:
        return None
    return round(100.0 * numerador / denominador, 2)


def promedio(valores):
    vals = [v for v in valores if v is not None]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 2)


def percentil(valores, p):
    """Percentil por rango más cercano (p en 0..100)."""
    vals = sorted(v for v in valores if v is not None)
    if not vals:
        return None
    rango = max(1, int(math.ceil(p / 100.0 * len(vals))))
    return vals[rango - 1]


# ---------------------------------------------------------------------------------------------
# Reglas elementales
# ---------------------------------------------------------------------------------------------
def clasificar_parada(estado, retraso_min, tol_retraso, tol_adelanto):
    """Puntualidad de una parada: puntual / atrasada / adelantada / omitida / pendiente.

    Límites inclusivos: con tolerancia 5 min, llegar exactamente 5 min tarde es puntual.
    """
    if estado == 'omitida':
        return 'omitida'
    if estado != 'atendida' or retraso_min is None:
        return 'pendiente'
    if retraso_min > tol_retraso:
        return 'atrasada'
    if retraso_min < -tol_adelanto:
        return 'adelantada'
    return 'puntual'


def severidad_retraso(minutos, tolerancia):
    """media: hasta 2× la tolerancia · alta: hasta 4× · crítica: más."""
    if minutos <= 2 * tolerancia:
        return 'media'
    if minutos <= 4 * tolerancia:
        return 'alta'
    return 'critica'


def distancia_a_trazado_m(lat, lon, trazado):
    """Distancia mínima (m) de un punto a una polilínea [(lat, lon), ...]."""
    if not trazado:
        return None
    if len(trazado) == 1:
        return geo_utils.haversine_m(lat, lon, trazado[0][0], trazado[0][1])
    return min(geo_utils.distancia_punto_segmento_m(lat, lon, a[0], a[1], b[0], b[1])
               for a, b in zip(trazado, trazado[1:]))


def analizar_desviacion(puntos, trazado, ancho_m, min_consecutivas):
    """Compara posiciones reales contra el corredor de la ruta.

    :param puntos: [(lat, lon), ...] posiciones válidas en orden cronológico
    :return: dict(max_m, pct_fuera, tramos=[(idx_ini, idx_fin, max_m)], desviado)
             Un tramo es una racha de >= min_consecutivas posiciones fuera del corredor.
    """
    vacio = {'max_m': 0.0, 'pct_fuera': None, 'tramos': [], 'desviado': False}
    if not puntos or not trazado or len(trazado) < 2:
        return vacio
    distancias = [distancia_a_trazado_m(la, lo, trazado) for la, lo in puntos]
    fuera = [d > ancho_m for d in distancias]
    tramos, inicio = [], None
    for i, f in enumerate(fuera + [False]):
        if f and inicio is None:
            inicio = i
        elif not f and inicio is not None:
            if i - inicio >= min_consecutivas:
                tramos.append((inicio, i - 1, round(max(distancias[inicio:i]), 1)))
            inicio = None
    return {
        'max_m': round(max(distancias), 1),
        'pct_fuera': porcentaje(sum(fuera), len(fuera)),
        'tramos': tramos,
        'desviado': bool(tramos),
    }


def detectar_huecos(fechas, inicio, fin, gap_min):
    """Huecos de reporte GPS mayores que gap_min dentro de la ventana [inicio, fin].

    :param fechas: fechas GPS ordenadas de las posiciones del viaje
    :return: [(desde, hasta, minutos)]
    """
    marcas = [f for f in fechas if (not inicio or f >= inicio) and (not fin or f <= fin)]
    if inicio:
        marcas = [inicio] + marcas
    if fin:
        marcas = marcas + [fin]
    huecos = []
    for a, b in zip(marcas, marcas[1:]):
        m = minutos_entre(a, b)
        if m is not None and m > gap_min:
            huecos.append((a, b, m))
    return huecos


def detectar_paradas(puntos, paradas, modo='segmento', max_s=360):
    """Réplica pura de la geocerca de transporte_gps_traccar (para medición y pruebas).

    :param puntos: [(fecha, lat, lon)] en orden cronológico
    :param paradas: [{'lat', 'lon', 'radio'}] en orden de secuencia
    :return: lista con la hora de llegada detectada por parada (None = no visitada)
    """
    llegadas = [None] * len(paradas)
    previa = None
    for fecha, lat, lon in puntos:
        usar = previa is not None and (fecha - previa[0]).total_seconds() <= max_s
        for i, p in enumerate(paradas):
            if llegadas[i] is not None:
                continue
            ok, _dist, t = geo_utils.paso_por_radio(
                p['lat'], p['lon'], p['radio'], (previa[1], previa[2]) if usar else None, (lat, lon), modo)
            if ok:
                llegadas[i] = (previa[0] + (fecha - previa[0]) * t) if t < 1.0 else fecha
        previa = (fecha, lat, lon)
    return llegadas


def comparar_deteccion(esperadas, detectadas):
    """Compara los tipos de incidencia esperados (escenario de prueba) con los detectados."""
    esperadas, detectadas = set(esperadas), set(detectadas)
    return {
        'correcta': esperadas == detectadas,
        'falsos_positivos': sorted(detectadas - esperadas),
        'falsos_negativos': sorted(esperadas - detectadas),
    }


def parsear_tipos(texto):
    """'retraso_parada, parada_omitida' -> {'retraso_parada', 'parada_omitida'}; valida los códigos."""
    if not texto:
        return set()
    tipos = {t.strip() for t in texto.replace(';', ',').split(',') if t.strip()}
    if tipos == {'ninguna'}:
        return set()
    invalidos = tipos - set(TIPOS_AUTOMATICOS)
    if invalidos:
        raise ValueError('Tipos de incidencia desconocidos: %s' % ', '.join(sorted(invalidos)))
    return tipos


# ---------------------------------------------------------------------------------------------
# Evaluación completa de un viaje
# ---------------------------------------------------------------------------------------------
def _incidencia(tipo, severidad, valor, unidad, descripcion, regla, ref=None):
    return {'tipo': tipo, 'severidad': severidad, 'valor': valor, 'unidad': unidad,
            'descripcion': descripcion, 'regla': regla, 'ref': ref}


def _evaluar_paradas(paradas, finalizado, tol):
    """Clasifica cada parada y genera las incidencias por parada."""
    filas, incidencias = [], []
    for p in sorted(paradas, key=lambda x: x['secuencia']):
        retraso = minutos_entre(p['hora_plan'], p['hora_real']) if p['estado'] == 'atendida' else None
        clase = clasificar_parada(p['estado'], retraso, tol['retraso_min'], tol['adelanto_min'])
        filas.append(dict(p, retraso=retraso, clase=clase))
        if clase == 'atrasada':
            incidencias.append(_incidencia(
                'retraso_parada', severidad_retraso(retraso, tol['retraso_min']), retraso, 'min',
                'Parada %s: llegada con %.1f min de retraso sobre la hora programada.' % (p['secuencia'], retraso),
                'retraso > %.0f min de tolerancia' % tol['retraso_min'], p.get('id')))
        elif clase == 'adelantada':
            incidencias.append(_incidencia(
                'adelanto_parada', 'baja', -retraso, 'min',
                'Parada %s: llegada %.1f min antes de la hora programada.' % (p['secuencia'], -retraso),
                'adelanto > %.0f min de tolerancia' % tol['adelanto_min'], p.get('id')))
        elif clase == 'omitida' and finalizado:
            incidencias.append(_incidencia(
                'parada_omitida', 'alta', 1, 'parada',
                'Parada %s no registrada como visitada (sin paso por su radio de detección).' % p['secuencia'],
                'parada sin llegada al finalizar el viaje', p.get('id')))
    return filas, incidencias


def _evaluar_gps(datos, fin_ventana, tol):
    """Reglas que requieren posiciones GPS: desviación del corredor y pérdida de señal."""
    incidencias = []
    posiciones = datos.get('posiciones') or []
    ancho = datos.get('ancho_corredor_m') or tol['ancho_corredor_m']
    desv = analizar_desviacion([(la, lo) for _f, la, lo in posiciones], datos.get('trazado') or [],
                               ancho, int(tol['fuera_consecutivas']))
    if desv['desviado']:
        incidencias.append(_incidencia(
            'desviacion_ruta', 'alta' if desv['max_m'] > 3 * ancho else 'media', desv['max_m'], 'm',
            '%d tramo(s) fuera del corredor; alejamiento máximo %.0f m del trazado de referencia.'
            % (len(desv['tramos']), desv['max_m']),
            '>= %d posiciones seguidas a más de %.0f m del trazado' % (tol['fuera_consecutivas'], ancho)))
    huecos = detectar_huecos([f for f, _la, _lo in posiciones], datos.get('salida_real'), fin_ventana,
                             tol['gap_senal_min'])
    if huecos:
        mayor = max(h[2] for h in huecos)
        incidencias.append(_incidencia(
            'perdida_senal', 'alta' if mayor > 3 * tol['gap_senal_min'] else 'media', mayor, 'min',
            '%d interrupción(es) de reporte GPS; la mayor de %.1f min (total %.1f min).'
            % (len(huecos), mayor, sum(h[2] for h in huecos)),
            'sin posiciones durante más de %.0f min' % tol['gap_senal_min']))
    return desv, huecos, incidencias


def _resumen_paradas(filas, datos, finalizado):
    """Conteos y retrasos por parada (sin reglas)."""
    programadas = len(filas)
    atendidas = [f for f in filas if f['clase'] in ('puntual', 'atrasada', 'adelantada')]
    destino = filas[-1] if filas else None
    destino_atendido = bool(destino and destino['estado'] == 'atendida')
    r = {
        'paradas_programadas': programadas,
        'paradas_atendidas': len(atendidas),
        'paradas_omitidas': len([f for f in filas if f['clase'] == 'omitida']),
        'paradas_puntuales': len([f for f in filas if f['clase'] == 'puntual']),
        'paradas_atrasadas': len([f for f in filas if f['clase'] == 'atrasada']),
        'paradas_adelantadas': len([f for f in filas if f['clase'] == 'adelantada']),
        'porcentaje_paradas': porcentaje(len(atendidas), programadas),
        'retraso_promedio_min': promedio([max(0.0, f['retraso']) for f in atendidas]),
        'retraso_maximo_min': max([f['retraso'] for f in atendidas], default=None),
        'retraso_acumulado_min': atendidas[-1]['retraso'] if atendidas else None,
        'retraso_inicio_min': minutos_entre(datos.get('salida_plan'), datos.get('salida_real')),
        'retraso_llegada_min': None,
        'duracion_estimada_min': minutos_entre(datos.get('salida_plan'), datos.get('llegada_plan')),
        'duracion_real_min': None,
        'diferencia_duracion_min': None,
        'diferencia_duracion_pct': None,
        'completo': finalizado and datos['estado'] == 'completed' and destino_atendido,
        'filas': filas,
    }
    r['porcentaje_puntualidad'] = porcentaje(r['paradas_puntuales'], len(atendidas))
    llegada_efectiva = destino['hora_real'] if destino_atendido else datos.get('llegada_real')
    return r, destino_atendido, llegada_efectiva


def _regla_retraso_inicio(r, tol):
    retraso = r['retraso_inicio_min']
    if retraso is None or retraso <= tol['retraso_min']:
        return []
    return [_incidencia(
        'retraso_inicio', severidad_retraso(retraso, tol['retraso_min']), retraso, 'min',
        'Salida con %.1f min de retraso sobre la hora programada.' % retraso,
        'retraso de salida > %.0f min' % tol['retraso_min'])]


def _regla_retraso_llegada(r, datos, llegada_efectiva, tol):
    r['retraso_llegada_min'] = minutos_entre(datos.get('llegada_plan'), llegada_efectiva)
    retraso = r['retraso_llegada_min']
    if retraso is None or retraso <= tol['retraso_min']:
        return []
    return [_incidencia(
        'retraso_llegada', severidad_retraso(retraso, tol['retraso_min']), retraso, 'min',
        'Llegada a destino con %.1f min de retraso.' % retraso,
        'retraso de llegada > %.0f min' % tol['retraso_min'])]


def _regla_diferencia_tiempo(r, datos, llegada_efectiva, tol):
    r['duracion_real_min'] = minutos_entre(datos.get('salida_real'), llegada_efectiva)
    if r['duracion_real_min'] is None or not r['duracion_estimada_min']:
        return []
    r['diferencia_duracion_min'] = round(r['duracion_real_min'] - r['duracion_estimada_min'], 2)
    r['diferencia_duracion_pct'] = porcentaje(r['diferencia_duracion_min'], r['duracion_estimada_min'])
    excede = (abs(r['diferencia_duracion_pct']) > tol['duracion_pct']
              and abs(r['diferencia_duracion_min']) > tol['retraso_min'])
    if not (r['completo'] and excede):
        return []
    return [_incidencia(
        'diferencia_tiempo', 'media', r['diferencia_duracion_min'], 'min',
        'Duración real %.1f min vs estimada %.1f min (%+.1f %%).'
        % (r['duracion_real_min'], r['duracion_estimada_min'], r['diferencia_duracion_pct']),
        '|diferencia| > %.0f %% y > %.0f min' % (tol['duracion_pct'], tol['retraso_min']))]


def _regla_recorrido_incompleto(r, datos):
    if not datos.get('salida_real') or r['completo']:
        return []
    motivo = 'cancelado en ruta' if datos['estado'] == 'cancelled' else 'no llegó a la parada de destino'
    return [_incidencia(
        'recorrido_incompleto', 'alta', r['porcentaje_paradas'] or 0.0, '%',
        'Recorrido incompleto (%s): %d de %d paradas visitadas.'
        % (motivo, r['paradas_atendidas'], r['paradas_programadas']),
        'destino no alcanzado o viaje cancelado después de iniciar')]


def _diferencia_distancia(r, datos):
    est, rec = datos.get('distancia_estimada_km') or 0.0, datos.get('distancia_recorrida_km')
    r['distancia_estimada_km'] = est
    r['diferencia_distancia_km'] = round(rec - est, 3) if (est and rec) else None
    r['diferencia_distancia_pct'] = (porcentaje(r['diferencia_distancia_km'], est)
                                     if r['diferencia_distancia_km'] is not None else None)


def _reglas_gps(r, datos, fin_ventana, tol):
    desv, huecos, incidencias = {'max_m': 0.0, 'pct_fuera': None, 'desviado': False}, [], []
    if datos.get('tiene_gps') and datos.get('salida_real'):
        desv, huecos, incidencias = _evaluar_gps(datos, fin_ventana, tol)
    r['max_desviacion_m'] = desv['max_m']
    r['porcentaje_fuera_corredor'] = desv['pct_fuera']
    r['desviado'] = desv['desviado']
    r['huecos_senal'] = len(huecos)
    r['max_hueco_senal_min'] = max([h[2] for h in huecos], default=0.0)
    return incidencias


def _veredicto(r, finalizado, tol):
    llegada_ok = r['retraso_llegada_min'] is None or r['retraso_llegada_min'] <= tol['retraso_min']
    r['puntual'] = bool(finalizado and r['completo'] and r['paradas_atrasadas'] == 0
                        and r['paradas_adelantadas'] == 0 and llegada_ok)
    r['cumple_ruta'] = bool(r['completo'] and r['paradas_omitidas'] == 0 and not r['desviado'])
    if not finalizado:
        r['resultado'] = 'en_curso'
    else:
        r['resultado'] = 'cumple' if (r['cumple_ruta'] and r['puntual']) else 'incumple'


def evaluar_viaje(datos, tol=None):
    """Evalúa un recorrido y devuelve indicadores e incidencias detectadas.

    Orquesta las reglas; cada una vive en su propia función y devuelve sus incidencias.

    :param datos: dict con
        estado ('completed'|'cancelled'|'in_progress'), salida_plan, llegada_plan, salida_real, llegada_real,
        paradas=[{id, secuencia, estado, hora_plan, hora_real}], tiene_gps (bool),
        posiciones=[(fecha, lat, lon)] válidas y ordenadas, trazado=[(lat, lon)], ancho_corredor_m,
        distancia_estimada_km, distancia_recorrida_km, ahora (para viajes en curso)
    :param tol: tolerancias (ver TOLERANCIAS_DEFECTO)
    """
    tol = dict(TOLERANCIAS_DEFECTO, **(tol or {}))
    finalizado = datos['estado'] in ESTADOS_FINALIZADOS
    filas, incidencias = _evaluar_paradas(datos.get('paradas') or [], finalizado, tol)
    r, destino_atendido, llegada_efectiva = _resumen_paradas(filas, datos, finalizado)

    incidencias += _regla_retraso_inicio(r, tol)
    if finalizado:  # llegada, duración e integridad solo con el viaje terminado
        if destino_atendido:
            incidencias += _regla_retraso_llegada(r, datos, llegada_efectiva, tol)
        incidencias += _regla_diferencia_tiempo(r, datos, llegada_efectiva, tol)
        incidencias += _regla_recorrido_incompleto(r, datos)
    _diferencia_distancia(r, datos)
    incidencias += _reglas_gps(r, datos, llegada_efectiva if finalizado else datos.get('ahora'), tol)
    _veredicto(r, finalizado, tol)
    r['incidencias'] = incidencias
    return r


# ---------------------------------------------------------------------------------------------
# Indicadores agregados (A7) a partir de filas de viajes evaluados
# ---------------------------------------------------------------------------------------------
def calcular_kpis_transporte(viajes, incidencias, dias_periodo):
    """Las 8 métricas de transporte obligatorias.

    :param viajes: dicts de viajes evaluados (finalizados con salida real) con las claves de evaluar_viaje
    :param incidencias: dicts {'tipo': ...} del mismo periodo
    :param dias_periodo: nº de días del periodo (para la frecuencia)
    """
    n = len(viajes)
    prog = sum(v['paradas_programadas'] for v in viajes)
    atend = sum(v['paradas_atendidas'] for v in viajes)
    punt = sum(v['paradas_puntuales'] for v in viajes)
    con_gps = [v for v in viajes if v.get('porcentaje_fuera_corredor') is not None]
    con_dist = [v for v in viajes if v.get('diferencia_distancia_km') is not None]
    duraciones = [v['duracion_real_min'] for v in viajes if v.get('completo') and v.get('duracion_real_min') is not None]
    por_tipo = {}
    for inc in incidencias:
        por_tipo[inc['tipo']] = por_tipo.get(inc['tipo'], 0) + 1
    return {
        'cumplimiento_rutas': {'valor': porcentaje(sum(1 for v in viajes if v['cumple_ruta']), n),
                               'num': sum(1 for v in viajes if v['cumple_ruta']), 'den': n},
        'puntualidad_paradas': {'valor': porcentaje(punt, atend), 'num': punt, 'den': atend},
        'puntualidad_viajes': {'valor': porcentaje(sum(1 for v in viajes if v['puntual']), n),
                               'num': sum(1 for v in viajes if v['puntual']), 'den': n},
        'retraso_promedio': {'valor': promedio([v['retraso_promedio_min'] for v in viajes]), 'den': n},
        'paradas_cumplidas': {'valor': porcentaje(atend, prog), 'num': atend, 'den': prog},
        'desviacion_ruta': {'valor': promedio([v['porcentaje_fuera_corredor'] for v in con_gps]),
                            'viajes_desviados': sum(1 for v in con_gps if v.get('desviado')),
                            'max_m': max([v.get('max_desviacion_m') or 0.0 for v in con_gps], default=0.0),
                            'den': len(con_gps)},
        'diferencia_distancia': {'valor': promedio([v['diferencia_distancia_pct'] for v in con_dist]),
                                 'km': promedio([v['diferencia_distancia_km'] for v in con_dist]),
                                 'den': len(con_dist)},
        'tiempo_promedio': {'valor': promedio(duraciones),
                            'estimado': promedio([v['duracion_estimada_min'] for v in viajes
                                                  if v.get('completo') and v.get('duracion_estimada_min')]),
                            'den': len(duraciones)},
        'incidencias': {'valor': len(incidencias),
                        'por_100_viajes': round(100.0 * len(incidencias) / n, 2) if n else None,
                        'por_dia': round(len(incidencias) / dias_periodo, 2) if dias_periodo else None,
                        'por_tipo': por_tipo},
    }


def pareto(conteos):
    """[(categoria, n)] ordenado desc con % y % acumulado."""
    total = sum(conteos.values())
    filas, acumulado = [], 0
    for cat, n in sorted(conteos.items(), key=lambda x: (-x[1], x[0])):
        acumulado += n
        filas.append({'categoria': cat, 'n': n, 'pct': porcentaje(n, total),
                      'pct_acumulado': porcentaje(acumulado, total)})
    return filas
