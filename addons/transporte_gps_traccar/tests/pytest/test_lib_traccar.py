# -*- coding: utf-8 -*-
from datetime import datetime
from unittest import mock

import pytest
import requests

import geo_utils
import traccar_client
import traccar_parser

# Par de puntos separados ~ 1 grado de latitud = 111.19 km
LAT, LON = -1.2491, -78.6167


def _punto_a_metros_norte(metros):
    """Latitud desplazada `metros` al norte de (LAT, LON)."""
    return LAT + metros / 111195.0


class TestHaversine:
    def test_misma_posicion_es_cero(self):
        assert geo_utils.haversine_m(LAT, LON, LAT, LON) == 0

    def test_un_grado_de_latitud(self):
        assert geo_utils.haversine_m(0, 0, 1, 0) == pytest.approx(111195, rel=1e-3)

    def test_simetria(self):
        a = geo_utils.haversine_m(LAT, LON, -1.26, -78.63)
        b = geo_utils.haversine_m(-1.26, -78.63, LAT, LON)
        assert a == pytest.approx(b)


class TestDentroDeRadio:
    """RF-04: 30 m con radio 50 -> visitada; 80 m -> no visitada; límite inclusivo."""

    def test_30m_radio_50(self):
        assert geo_utils.dentro_de_radio(_punto_a_metros_norte(30), LON, LAT, LON, 50)

    def test_80m_radio_50(self):
        assert not geo_utils.dentro_de_radio(_punto_a_metros_norte(80), LON, LAT, LON, 50)

    def test_limite_exacto(self):
        d = geo_utils.haversine_m(_punto_a_metros_norte(50), LON, LAT, LON)
        assert geo_utils.dentro_de_radio(_punto_a_metros_norte(50), LON, LAT, LON, d)
        assert not geo_utils.dentro_de_radio(_punto_a_metros_norte(50), LON, LAT, LON, d - 0.01)


class TestCoordenadas:
    @pytest.mark.parametrize('lat,lon,esperado', [
        (-1.2, -78.6, True), (90, 180, True), (-90, -180, True),
        (0, 0, False), (90.0001, 0, False), (0, 180.0001, False),
        (None, 5, False), (5, None, False),
    ])
    def test_validez(self, lat, lon, esperado):
        assert geo_utils.coordenadas_validas(lat, lon) is esperado

    def test_cero_en_un_solo_eje_es_valido(self):
        assert geo_utils.coordenadas_validas(0.0, -78.6)


class TestConversionesYDistancia:
    def test_nudos_a_kmh(self):
        assert geo_utils.nudos_a_kmh(10) == 18.52
        assert geo_utils.nudos_a_kmh(None) == 0.0

    def test_distancia_total_vacia_o_un_punto(self):
        assert geo_utils.distancia_total_km([]) == 0.0
        assert geo_utils.distancia_total_km([(LAT, LON)]) == 0.0

    def test_distancia_total_suma_tramos(self):
        pts = [(0, 0), (0.5, 0), (1, 0)]
        assert geo_utils.distancia_total_km(pts) == pytest.approx(111.195, abs=0.2)


class TestSenal:
    AHORA = datetime(2026, 11, 14, 12, 0, 0)

    def test_sin_posicion_esta_desactualizada(self):
        assert geo_utils.senal_desactualizada(None, self.AHORA, 5)

    def test_reciente(self):
        assert not geo_utils.senal_desactualizada(datetime(2026, 11, 14, 11, 57), self.AHORA, 5)

    def test_exactamente_en_el_limite_no_se_marca(self):
        assert not geo_utils.senal_desactualizada(datetime(2026, 11, 14, 11, 55), self.AHORA, 5)

    def test_un_segundo_sobre_el_limite(self):
        assert geo_utils.senal_desactualizada(datetime(2026, 11, 14, 11, 54, 59), self.AHORA, 5)


RAW = {
    'id': 77, 'deviceId': 3, 'latitude': -1.2491, 'longitude': -78.6167, 'speed': 10.0,
    'valid': True, 'fixTime': '2026-11-14T17:00:00.000+00:00',
}


class TestParser:
    def test_posicion_completa(self):
        p = traccar_parser.parse_posicion(RAW)
        assert p['traccar_position_id'] == 77
        assert p['traccar_device_id'] == 3
        assert p['velocidad_kmh'] == 18.52
        assert p['fecha_gps'] == datetime(2026, 11, 14, 17, 0, 0)
        assert p['valida'] is True

    def test_zona_horaria_se_normaliza_a_utc(self):
        raw = dict(RAW, fixTime='2026-11-14T12:00:00-05:00')
        assert traccar_parser.parse_posicion(raw)['fecha_gps'] == datetime(2026, 11, 14, 17, 0, 0)

    def test_sufijo_z(self):
        assert traccar_parser.parse_fecha_traccar('2026-11-14T17:00:00Z') == datetime(2026, 11, 14, 17, 0, 0)

    @pytest.mark.parametrize('campo', ['id', 'deviceId', 'latitude', 'longitude'])
    def test_campo_obligatorio_faltante(self, campo):
        raw = {k: v for k, v in RAW.items() if k != campo}
        with pytest.raises(ValueError):
            traccar_parser.parse_posicion(raw)

    def test_no_es_objeto(self):
        with pytest.raises(ValueError):
            traccar_parser.parse_posicion([1, 2])

    def test_fecha_ausente(self):
        with pytest.raises(ValueError):
            traccar_parser.parse_posicion({k: v for k, v in RAW.items() if k != 'fixTime'})

    def test_valid_false_de_traccar(self):
        assert traccar_parser.parse_posicion(dict(RAW, valid=False))['valida'] is False

    def test_coordenada_cero_es_invalida(self):
        assert traccar_parser.parse_posicion(dict(RAW, latitude=0, longitude=0))['valida'] is False

    def test_sin_velocidad_es_cero(self):
        raw = {k: v for k, v in RAW.items() if k != 'speed'}
        assert traccar_parser.parse_posicion(raw)['velocidad_kmh'] == 0.0

    def test_forward_envuelto(self):
        assert traccar_parser.parse_payload_forward({'position': RAW, 'device': {}})['traccar_position_id'] == 77

    def test_forward_directo(self):
        assert traccar_parser.parse_payload_forward(RAW)['traccar_position_id'] == 77

    def test_formato_fecha_api(self):
        assert traccar_parser.formato_fecha_api(datetime(2026, 1, 2, 3, 4, 5)) == '2026-01-02T03:04:05Z'


def _resp(status=200, data=None, json_error=False):
    r = mock.Mock(status_code=status)
    if json_error:
        r.json.side_effect = ValueError()
    else:
        r.json.return_value = data
    return r


class TestClient:
    def test_sin_url(self):
        with pytest.raises(traccar_client.TraccarError):
            traccar_client.TraccarClient('')

    def test_token_usa_bearer(self):
        c = traccar_client.TraccarClient('http://x/', token='abc', user='u', password='p')
        assert c.headers['Authorization'] == 'Bearer abc'
        assert c.auth is None
        assert c.base_url == 'http://x'

    def test_basic_auth(self):
        c = traccar_client.TraccarClient('http://x', user='u', password='p')
        assert c.auth == ('u', 'p')

    def test_get_positions_arma_la_consulta(self):
        c = traccar_client.TraccarClient('http://x', token='t')
        with mock.patch('requests.get', return_value=_resp(data=[RAW])) as get:
            assert c.get_positions(3, 'A', 'B') == [RAW]
        args, kwargs = get.call_args
        assert args[0] == 'http://x/api/positions'
        assert kwargs['params'] == {'deviceId': 3, 'from': 'A', 'to': 'B'}

    @pytest.mark.parametrize('status', [401, 403, 500, 404])
    def test_http_error(self, status):
        c = traccar_client.TraccarClient('http://x', token='t')
        with mock.patch('requests.get', return_value=_resp(status=status)):
            with pytest.raises(traccar_client.TraccarError):
                c.get_devices()

    def test_json_invalido(self):
        c = traccar_client.TraccarClient('http://x', token='t')
        with mock.patch('requests.get', return_value=_resp(json_error=True)):
            with pytest.raises(traccar_client.TraccarError):
                c.get_devices()

    def test_red_caida(self):
        c = traccar_client.TraccarClient('http://x', token='t')
        with mock.patch('requests.get', side_effect=requests.ConnectionError('boom')):
            with pytest.raises(traccar_client.TraccarError):
                c.get_devices()

    def test_ultima_posicion_vacia(self):
        c = traccar_client.TraccarClient('http://x', token='t')
        with mock.patch('requests.get', return_value=_resp(data=[])):
            assert c.get_ultima_posicion(3) is None


class TestGeocercaPorSegmento:
    """Mejora PDCA: detección de paso por la parada entre dos muestras GPS."""

    def _este(self, metros):
        return LON + metros / 111195.0

    def test_proyeccion_en_el_medio_del_tramo(self):
        # parada en (LAT, LON); tramo de 100 m al oeste a 100 m al este, desplazado 20 m al norte
        d, t = geo_utils.proyeccion_en_segmento(LAT, LON, _punto_a_metros_norte(20), self._este(-100),
                                                _punto_a_metros_norte(20), self._este(100))
        assert 19.5 < d < 20.5
        assert t == pytest.approx(0.5, abs=0.01)

    def test_proyeccion_fuera_del_tramo_usa_el_extremo(self):
        d, t = geo_utils.proyeccion_en_segmento(LAT, LON, LAT, self._este(50), LAT, self._este(150))
        assert t == 0.0 and 49 < d < 51

    def test_tramo_degenerado(self):
        d, t = geo_utils.proyeccion_en_segmento(LAT, LON, _punto_a_metros_norte(10), LON,
                                                _punto_a_metros_norte(10), LON)
        assert t == 0.0 and 9.9 < d < 10.1
        assert geo_utils.distancia_punto_segmento_m(LAT, LON, LAT, LON, LAT, LON) == 0

    def test_paso_por_radio_muestra_dentro(self):
        ok, d, t = geo_utils.paso_por_radio(LAT, LON, 30, None, (_punto_a_metros_norte(10), LON))
        assert ok and t == 1.0 and d < 11

    def test_paso_por_radio_segmento_vs_punto(self):
        previa, actual = (LAT, self._este(-80)), (LAT, self._este(80))
        assert geo_utils.paso_por_radio(LAT, LON, 30, previa, actual, 'punto')[0] is False
        ok, d, t = geo_utils.paso_por_radio(LAT, LON, 30, previa, actual, 'segmento')
        assert ok and d < 1 and t == pytest.approx(0.5, abs=0.01)

    def test_paso_por_radio_sin_previa_o_lejos(self):
        lejos = (LAT, self._este(500))
        assert geo_utils.paso_por_radio(LAT, LON, 30, None, lejos)[0] is False
        assert geo_utils.paso_por_radio(LAT, LON, 30, (_punto_a_metros_norte(200), self._este(400)), lejos)[0] is False
