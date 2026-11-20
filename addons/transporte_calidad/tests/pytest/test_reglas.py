# -*- coding: utf-8 -*-
"""Pruebas de caja blanca de las reglas de detección y fórmulas de indicadores (sin Odoo).

Los identificadores CP-xx remiten a la matriz de casos de prueba (docs/PLAN_PRUEBAS.md).
"""
from datetime import datetime, timedelta

import pytest

import reglas
import simulador

T0 = datetime(2026, 11, 19, 13, 0, 0)  # 08:00 hora de Ecuador (UTC-5)

# Paradas reales de la ruta DEMO-RUT-01 (Ambato)
R1 = [
    {'lat': -1.238400, 'lon': -78.621500, 'radio': 35, 't_min': 0},
    {'lat': -1.242300, 'lon': -78.625400, 'radio': 30, 't_min': 8},
    {'lat': -1.247100, 'lon': -78.629800, 'radio': 40, 't_min': 16},
    {'lat': -1.251500, 'lon': -78.633200, 'radio': 30, 't_min': 23},
    {'lat': -1.256000, 'lon': -78.637500, 'radio': 35, 't_min': 30},
    {'lat': -1.261200, 'lon': -78.641000, 'radio': 45, 't_min': 38},
    {'lat': -1.268500, 'lon': -78.647000, 'radio': 50, 't_min': 45},
]
R2 = [
    {'lat': -1.244000, 'lon': -78.612000, 'radio': 40, 't_min': 0},
    {'lat': -1.250500, 'lon': -78.618500, 'radio': 35, 't_min': 7},
    {'lat': -1.247100, 'lon': -78.629800, 'radio': 40, 't_min': 15},
    {'lat': -1.256000, 'lon': -78.637500, 'radio': 35, 't_min': 22},
    {'lat': -1.258000, 'lon': -78.624000, 'radio': 30, 't_min': 29},
    {'lat': -1.268500, 'lon': -78.647000, 'radio': 50, 't_min': 35},
]
R3 = [
    {'lat': -1.233000, 'lon': -78.628000, 'radio': 40, 't_min': 0},
    {'lat': -1.238400, 'lon': -78.621500, 'radio': 35, 't_min': 9},
    {'lat': -1.250500, 'lon': -78.618500, 'radio': 35, 't_min': 20},
    {'lat': -1.261200, 'lon': -78.641000, 'radio': 45, 't_min': 31},
    {'lat': -1.272000, 'lon': -78.652000, 'radio': 50, 't_min': 40},
]
RUTAS = [R1, R2, R3]


def parada(seq, estado, plan_min, real_min=None):
    return {'id': seq, 'secuencia': seq, 'estado': estado, 'hora_plan': T0 + timedelta(minutes=plan_min),
            'hora_real': T0 + timedelta(minutes=real_min) if real_min is not None else None}


def viaje_base(**kw):
    datos = {
        'estado': 'completed', 'salida_plan': T0, 'llegada_plan': T0 + timedelta(minutes=30),
        'salida_real': T0, 'llegada_real': T0 + timedelta(minutes=30),
        'paradas': [parada(1, 'atendida', 0, 0), parada(2, 'atendida', 15, 15), parada(3, 'atendida', 30, 30)],
        'tiene_gps': False,
    }
    datos.update(kw)
    return datos


def tipos(resultado):
    return {i['tipo'] for i in resultado['incidencias']}


# ----------------------------------------------------------------------------- utilidades
def test_minutos_entre_y_porcentaje():
    assert reglas.minutos_entre(T0, T0 + timedelta(minutes=8)) == 8.0
    assert reglas.minutos_entre(T0, T0 - timedelta(seconds=90)) == -1.5
    assert reglas.minutos_entre(None, T0) is None
    assert reglas.porcentaje(1, 3) == 33.33
    assert reglas.porcentaje(5, 0) is None  # indicador no aplicable, no 0 %


def test_promedio_y_percentil():
    assert reglas.promedio([1, None, 3]) == 2.0
    assert reglas.promedio([]) is None
    assert reglas.percentil([10, 20, 30, 40], 95) == 40
    assert reglas.percentil([10, 20, 30, 40], 50) == 20


# ----------------------------------------------------------------------------- CP-05/06 puntualidad
@pytest.mark.parametrize('retraso,esperado', [
    (0.0, 'puntual'),
    (5.0, 'puntual'),        # límite inclusivo
    (5.01, 'atrasada'),      # justo sobre la tolerancia
    (8.0, 'atrasada'),       # ejemplo del enunciado: 08:15 + 5 -> 08:23
    (-2.0, 'puntual'),       # límite inclusivo de adelanto
    (-2.5, 'adelantada'),
])
def test_clasificar_parada_limites(retraso, esperado):
    assert reglas.clasificar_parada('atendida', retraso, 5, 2) == esperado


def test_clasificar_parada_omitida_y_pendiente():
    assert reglas.clasificar_parada('omitida', None, 5, 2) == 'omitida'
    assert reglas.clasificar_parada('pendiente', None, 5, 2) == 'pendiente'


def test_ejemplo_enunciado_0815_0823():
    """CP-05: parada prevista 08:15, tolerancia 5 min, llegada 08:23 -> retraso de 8 min e incumplimiento."""
    datos = viaje_base(paradas=[parada(1, 'atendida', 0, 0), parada(2, 'atendida', 15, 23),
                                parada(3, 'atendida', 30, 30)])
    r = reglas.evaluar_viaje(datos)
    inc = [i for i in r['incidencias'] if i['tipo'] == 'retraso_parada']
    assert len(inc) == 1 and inc[0]['valor'] == 8.0 and inc[0]['ref'] == 2
    assert r['paradas_atrasadas'] == 1
    assert r['puntual'] is False and r['resultado'] == 'incumple'


@pytest.mark.parametrize('minutos,sev', [(5.5, 'media'), (10, 'media'), (10.5, 'alta'), (20, 'alta'), (21, 'critica')])
def test_severidad_retraso(minutos, sev):
    assert reglas.severidad_retraso(minutos, 5) == sev


# ----------------------------------------------------------------------------- viaje completo
def test_viaje_perfecto_cumple():
    r = reglas.evaluar_viaje(viaje_base())
    assert r['incidencias'] == []
    assert r['porcentaje_paradas'] == 100.0 and r['porcentaje_puntualidad'] == 100.0
    assert r['cumple_ruta'] and r['puntual'] and r['resultado'] == 'cumple'
    assert r['retraso_promedio_min'] == 0.0 and r['duracion_real_min'] == 30.0


def test_parada_omitida_y_recorrido_incompleto():
    """CP-07: parada intermedia omitida; CP-08: destino no alcanzado."""
    omit = viaje_base(paradas=[parada(1, 'atendida', 0, 0), parada(2, 'omitida', 15),
                               parada(3, 'atendida', 30, 30)])
    r = reglas.evaluar_viaje(omit)
    assert tipos(r) == {'parada_omitida'}
    assert r['porcentaje_paradas'] == 66.67 and r['cumple_ruta'] is False

    incompleto = viaje_base(paradas=[parada(1, 'atendida', 0, 0), parada(2, 'atendida', 15, 15),
                                     parada(3, 'omitida', 30)])
    r = reglas.evaluar_viaje(incompleto)
    assert tipos(r) == {'parada_omitida', 'recorrido_incompleto'}
    assert r['completo'] is False and r['retraso_llegada_min'] is None


def test_cancelado_en_ruta_es_incompleto():
    datos = viaje_base(estado='cancelled', paradas=[parada(1, 'atendida', 0, 0), parada(2, 'omitida', 15),
                                                    parada(3, 'omitida', 30)])
    r = reglas.evaluar_viaje(datos)
    assert 'recorrido_incompleto' in tipos(r)
    assert 'cancelado' in [i for i in r['incidencias'] if i['tipo'] == 'recorrido_incompleto'][0]['descripcion']


def test_viaje_en_curso_no_genera_omisiones():
    datos = viaje_base(estado='in_progress', llegada_real=None,
                       paradas=[parada(1, 'atendida', 0, 0), parada(2, 'pendiente', 15), parada(3, 'pendiente', 30)])
    r = reglas.evaluar_viaje(datos)
    assert r['resultado'] == 'en_curso' and r['incidencias'] == []
    assert r['retraso_acumulado_min'] == 0.0


def test_retraso_inicio_y_llegada():
    datos = viaje_base(salida_real=T0 + timedelta(minutes=7),
                       paradas=[parada(1, 'atendida', 0, 7), parada(2, 'atendida', 15, 22),
                                parada(3, 'atendida', 30, 37)])
    r = reglas.evaluar_viaje(datos)
    assert tipos(r) == {'retraso_inicio', 'retraso_parada', 'retraso_llegada'}
    assert r['retraso_inicio_min'] == 7.0 and r['retraso_llegada_min'] == 7.0
    assert r['diferencia_duracion_min'] == 0.0  # desplazado, no más lento


def test_diferencia_tiempo_umbral():
    """CP-09: +40 % de duración dispara diferencia_tiempo; +10 % no."""
    lento = viaje_base(llegada_plan=T0 + timedelta(minutes=30),
                       paradas=[parada(1, 'atendida', 0, 0), parada(2, 'atendida', 15, 19),
                                parada(3, 'atendida', 30, 42)])
    r = reglas.evaluar_viaje(lento)
    assert 'diferencia_tiempo' in tipos(r) and r['diferencia_duracion_pct'] == 40.0
    leve = viaje_base(paradas=[parada(1, 'atendida', 0, 0), parada(2, 'atendida', 15, 16),
                               parada(3, 'atendida', 30, 33)])
    assert 'diferencia_tiempo' not in tipos(reglas.evaluar_viaje(leve))


def test_tolerancias_configurables():
    datos = viaje_base(paradas=[parada(1, 'atendida', 0, 0), parada(2, 'atendida', 15, 23),
                                parada(3, 'atendida', 30, 30)])
    assert 'retraso_parada' not in tipos(reglas.evaluar_viaje(datos, {'retraso_min': 10}))


# ----------------------------------------------------------------------------- GPS: corredor y señal
TRAZADO = [(-1.2400, -78.6200), (-1.2500, -78.6200)]  # tramo norte-sur de ~1.1 km


def test_distancia_a_trazado():
    assert reglas.distancia_a_trazado_m(-1.2450, -78.6200, TRAZADO) < 1
    d = reglas.distancia_a_trazado_m(-1.2450, -78.6200 + 200 / 111320.0, TRAZADO)
    assert 199 < d < 201
    assert reglas.distancia_a_trazado_m(0, 0, []) is None


def test_desviacion_requiere_racha_consecutiva():
    """CP-10: 3 posiciones seguidas a 300 m => desvío; 2 aisladas => ruido."""
    dentro = (-1.2450, -78.6200)
    fuera = (-1.2450, -78.6200 + 300 / 111320.0)
    r = reglas.analizar_desviacion([dentro, fuera, fuera, fuera, dentro], TRAZADO, 150, 3)
    assert r['desviado'] and len(r['tramos']) == 1 and r['pct_fuera'] == 60.0
    r = reglas.analizar_desviacion([dentro, fuera, fuera, dentro, fuera], TRAZADO, 150, 3)
    assert not r['desviado'] and r['max_m'] > 290


def test_desviacion_sin_trazado_no_evalua():
    assert reglas.analizar_desviacion([(-1.24, -78.62)], [], 150, 3)['desviado'] is False


def test_detectar_huecos_incluye_bordes():
    fechas = [T0 + timedelta(minutes=m) for m in (1, 2, 8, 9)]
    huecos = reglas.detectar_huecos(fechas, T0, T0 + timedelta(minutes=10), 3)
    assert [h[2] for h in huecos] == [6.0]
    huecos = reglas.detectar_huecos([], T0, T0 + timedelta(minutes=10), 3)
    assert [h[2] for h in huecos] == [10.0]  # viaje con GPS sin ninguna posición


def test_viaje_gps_sin_posiciones_es_perdida_de_senal():
    r = reglas.evaluar_viaje(viaje_base(tiene_gps=True, posiciones=[], trazado=TRAZADO))
    assert tipos(r) == {'perdida_senal'}


def test_viaje_manual_sin_gps_no_aplica_reglas_gps():
    r = reglas.evaluar_viaje(viaje_base(tiene_gps=False, posiciones=[]))
    assert r['porcentaje_fuera_corredor'] is None and r['incidencias'] == []


# ----------------------------------------------------------------------------- comparación y parseo
def test_comparar_deteccion():
    c = reglas.comparar_deteccion({'retraso_parada'}, {'retraso_parada', 'perdida_senal'})
    assert not c['correcta'] and c['falsos_positivos'] == ['perdida_senal'] and c['falsos_negativos'] == []
    assert reglas.comparar_deteccion(set(), set())['correcta']


def test_parsear_tipos():
    assert reglas.parsear_tipos('retraso_parada, parada_omitida') == {'retraso_parada', 'parada_omitida'}
    assert reglas.parsear_tipos('ninguna') == set()
    with pytest.raises(ValueError):
        reglas.parsear_tipos('retraso_parada, inventada')


# ----------------------------------------------------------------------------- KPIs agregados
def test_kpis_transporte_formulas():
    """CP-11: fórmulas de A7 con un conjunto de 2 viajes de valores conocidos."""
    ok = reglas.evaluar_viaje(viaje_base())
    malo = reglas.evaluar_viaje(viaje_base(paradas=[parada(1, 'atendida', 0, 0), parada(2, 'atendida', 15, 23),
                                                    parada(3, 'omitida', 30)]))
    k = reglas.calcular_kpis_transporte([ok, malo], ok['incidencias'] + malo['incidencias'], 2)
    assert k['cumplimiento_rutas']['valor'] == 50.0
    assert k['paradas_cumplidas']['valor'] == round(100 * 5 / 6, 2)      # 5 atendidas de 6
    assert k['puntualidad_paradas']['valor'] == 80.0                    # 4 puntuales de 5 atendidas
    assert k['retraso_promedio']['valor'] == round((0 + 4.0) / 2, 2)    # promedio de promedios por viaje
    assert k['incidencias']['valor'] == 3 and k['incidencias']['por_dia'] == 1.5
    assert k['incidencias']['por_tipo'] == {'retraso_parada': 1, 'parada_omitida': 1, 'recorrido_incompleto': 1}


def test_kpis_sin_viajes_no_dividen_por_cero():
    k = reglas.calcular_kpis_transporte([], [], 0)
    assert k['cumplimiento_rutas']['valor'] is None and k['incidencias']['por_100_viajes'] is None


def test_pareto():
    filas = reglas.pareto({'a': 1, 'b': 6, 'c': 3})
    assert [f['categoria'] for f in filas] == ['b', 'c', 'a']
    assert filas[-1]['pct_acumulado'] == 100.0 and filas[0]['pct'] == 60.0


# ----------------------------------------------------------------------------- geocerca y simulador
def _paradas_geo(ruta):
    return [{'lat': p['lat'], 'lon': p['lon'], 'radio': p['radio']} for p in ruta]


def test_geocerca_segmento_detecta_paso_entre_muestras():
    """CP-12 (mejora PDCA): muestras a 80 m antes y después de la parada (radio 30 m)."""
    p = [{'lat': -1.2450, 'lon': -78.6200, 'radio': 30}]
    antes = (T0, -1.2450 + 80 / 111320.0, -78.6200)
    despues = (T0 + timedelta(seconds=120), -1.2450 - 80 / 111320.0, -78.6200)
    assert reglas.detectar_paradas([antes, despues], p, 'punto') == [None]
    llegada = reglas.detectar_paradas([antes, despues], p, 'segmento')[0]
    assert llegada == T0 + timedelta(seconds=60)  # hora interpolada en el punto más cercano


def test_geocerca_no_interpola_a_traves_de_perdida_de_senal():
    p = [{'lat': -1.2450, 'lon': -78.6200, 'radio': 30}]
    antes = (T0, -1.2450 + 80 / 111320.0, -78.6200)
    despues = (T0 + timedelta(minutes=10), -1.2450 - 80 / 111320.0, -78.6200)
    assert reglas.detectar_paradas([antes, despues], p, 'segmento', max_s=360) == [None]


def _evaluar_simulado(ruta, escenario, intervalo, modo='segmento'):
    salida = T0
    sim = simulador.generar_recorrido(ruta, salida, escenario, intervalo, semilla=7)
    puntos = [(f, la, lo) for f, la, lo, _v in sim['puntos']]
    llegadas = reglas.detectar_paradas(puntos, _paradas_geo(ruta), modo)
    paradas = [{'id': i, 'secuencia': i + 1, 'estado': 'atendida' if ll else 'omitida',
                'hora_plan': salida + timedelta(minutes=p['t_min']), 'hora_real': ll}
               for i, (p, ll) in enumerate(zip(ruta, llegadas))]
    datos = {
        'estado': 'completed', 'salida_plan': salida, 'llegada_plan': salida + timedelta(minutes=ruta[-1]['t_min']),
        'salida_real': sim['salida_real'], 'llegada_real': sim['llegada_real'], 'paradas': paradas,
        'tiene_gps': True, 'posiciones': puntos, 'trazado': [(p['lat'], p['lon']) for p in ruta],
    }
    return sim, reglas.evaluar_viaje(datos)


@pytest.mark.parametrize('escenario,ruta_idx,intervalo', [
    (e, r, i) for (e, r, _b, _h, i) in simulador.PLAN_DIEZ])
def test_plan_diez_deteccion_correcta(escenario, ruta_idx, intervalo):
    """CP-13: los 10 recorridos simulados producen exactamente las incidencias esperadas."""
    sim, r = _evaluar_simulado(RUTAS[ruta_idx], escenario, intervalo)
    assert tipos(r) == sim['esperadas'], r['incidencias']


@pytest.mark.parametrize('escenario', sorted(set(simulador.ESCENARIOS) - {'muestreo_disperso'}))
@pytest.mark.parametrize('ruta_idx', [0, 1, 2])
def test_todos_los_escenarios_en_todas_las_rutas(escenario, ruta_idx):
    sim, r = _evaluar_simulado(RUTAS[ruta_idx], escenario, 15)
    assert tipos(r) == sim['esperadas'], r['incidencias']


@pytest.mark.parametrize('ruta_idx', [0, 1, 2])
def test_muestreo_disperso_segmento_nunca_peor_que_punto(ruta_idx):
    """Con reportes cada 120 s el modo segmento reduce (sin eliminar en giros) las falsas omisiones."""
    _s, punto = _evaluar_simulado(RUTAS[ruta_idx], 'muestreo_disperso', 120, modo='punto')
    _s, segm = _evaluar_simulado(RUTAS[ruta_idx], 'muestreo_disperso', 120, modo='segmento')
    assert segm['paradas_omitidas'] <= punto['paradas_omitidas']


@pytest.mark.parametrize('ruta_idx', [0, 1, 2])
def test_intervalo_recomendado_30s_sin_falsas_omisiones(ruta_idx):
    """Estandarización (Act del PDCA): con Traccar Client a 30 s no hay falsas omisiones."""
    _s, r = _evaluar_simulado(RUTAS[ruta_idx], 'muestreo_disperso', 30)
    assert r['paradas_omitidas'] == 0


def test_simulador_es_determinista_y_valida_entradas():
    a = simulador.generar_recorrido(R1, T0, 'puntual', 15, semilla=1)
    b = simulador.generar_recorrido(R1, T0, 'puntual', 15, semilla=1)
    assert a['puntos'] == b['puntos']
    with pytest.raises(ValueError):
        simulador.generar_recorrido(R1, T0, 'inexistente')
    with pytest.raises(ValueError):
        simulador.generar_recorrido(R1[:2], T0, 'puntual')


def test_muestreo_disperso_falla_con_geocerca_por_punto():
    """Situación ANTES de la mejora: con reportes cada 120 s el modo 'punto' inventa paradas omitidas."""
    _sim, r = _evaluar_simulado(R1, 'muestreo_disperso', 120, modo='punto')
    assert 'parada_omitida' in tipos(r)
