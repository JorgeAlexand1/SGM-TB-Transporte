# -*- coding: utf-8 -*-
"""Pruebas de la pantalla «En vivo»: líneas, tramo del bus, llegadas estimadas y confianza."""
from datetime import timedelta

from odoo import fields
from odoo.tests.common import HttpCase, new_test_user, tagged

from odoo.addons.transporte_calidad.tests.test_calidad import CalidadCommon


def _a_dt(iso):
    return fields.Datetime.from_string(iso)


@tagged('post_install', '-at_install')
class TestEnVivo(CalidadCommon):

    def _linea(self, datos, ruta):
        return next(l for l in datos['lineas'] if l['id'] == ruta.id)

    def test_lineas_con_color_y_paradas(self):
        datos = self.env['transporte.en.vivo'].get_en_vivo()
        for ruta in self.rutas:
            linea = self._linea(datos, ruta)
            self.assertRegex(linea['color'], r'^#[0-9A-F]{6}$')
            self.assertEqual([p['nombre'] for p in linea['paradas']],
                             ruta.parada_ids.sorted('secuencia').mapped('parada_id.name'))
            self.assertGreaterEqual(len(linea['trazado']), 2)
        colores = [self._linea(datos, r)['color'] for r in self.rutas]
        self.assertEqual(len(set(colores)), len(colores), 'cada línea tiene su color')

    def test_bus_sin_gps_estima_por_horario(self):
        """Sin posición GPS no se inventa un punto en el mapa: la confianza es «según horario»."""
        viaje = self._viaje_manual()
        linea = self._linea(self.env['transporte.en.vivo'].get_en_vivo(), self.ruta1)
        bus = next(b for b in linea['buses'] if b['viaje_id'] == viaje.id)
        self.assertIsNone(bus['lat'])
        self.assertEqual(bus['confianza'], 'baja')
        self.assertEqual(bus['tramo'], -1)
        primera = viaje.parada_line_ids.sorted('secuencia')[0]
        self.assertEqual(bus['proxima']['nombre'], primera.parada_id.name)
        self.assertEqual(_a_dt(bus['proxima']['eta']), primera.hora_planificada)
        self.assertEqual(bus['estado'], 'a_tiempo')

    def test_tramo_y_eta_con_retraso(self):
        """Tras pasar la primera parada con retraso, el bus va en el tramo 0 y las llegadas se corren."""
        viaje = self._viaje_manual()
        lineas = viaje.parada_line_ids.sorted('secuencia')
        lineas[0].write({'estado_parada': 'atendida',
                         'hora_llegada_real': lineas[0].hora_planificada + timedelta(minutes=8)})
        viaje.retraso_acumulado_min = 8
        linea = self._linea(self.env['transporte.en.vivo'].get_en_vivo(), self.ruta1)
        bus = next(b for b in linea['buses'] if b['viaje_id'] == viaje.id)
        self.assertEqual(bus['tramo'], 0)
        self.assertEqual(bus['visitadas'], 1)
        self.assertEqual(bus['paradas'][0]['retraso'], 8.0)
        self.assertEqual(bus['proxima']['nombre'], lineas[1].parada_id.name)
        self.assertEqual(_a_dt(bus['proxima']['eta']), lineas[1].hora_planificada + timedelta(minutes=8))
        self.assertEqual(bus['estado'], 'retraso')  # 8 min > tolerancia de 5

    def test_omitida_cuenta_como_pasada(self):
        viaje = self._viaje_manual()
        lineas = viaje.parada_line_ids.sorted('secuencia')
        lineas[0].estado_parada = 'omitida'
        bus = next(b for b in self._linea(self.env['transporte.en.vivo'].get_en_vivo(), self.ruta1)['buses']
                   if b['viaje_id'] == viaje.id)
        self.assertEqual(bus['tramo'], 0)
        self.assertFalse(bus['paradas'][0]['eta'])
        self.assertEqual(bus['visitadas'], 0)

    def test_proximas_salidas(self):
        salida = fields.Datetime.now() + timedelta(hours=1)
        viaje = self.env['transporte.viaje'].create({
            'ruta_id': self.ruta1.id, 'vehicle_id': self.bus1.id, 'driver_id': self.conductor.id,
            'fecha_viaje': salida.date(), 'hora_salida_planificada': salida,
            'hora_llegada_planificada': salida + timedelta(minutes=self.ruta1.tiempo_estimado_min)})
        viaje.action_programar()
        linea = self._linea(self.env['transporte.en.vivo'].get_en_vivo(), self.ruta1)
        self.assertIn(viaje.id, [s['viaje_id'] for s in linea['salidas']])
        self.assertLessEqual(len(linea['salidas']), 3)

    def test_usuario_consulta_puede_ver(self):
        self._viaje_manual()
        consulta = new_test_user(self.env, login='tev_consulta', groups='transporte_core.group_transporte_user')
        datos = self.env['transporte.en.vivo'].with_user(consulta).get_en_vivo()
        self.assertGreaterEqual(datos['total_buses'], 1)


@tagged('post_install', '-at_install', '-standard', 'ui')
class TestUiEnVivo(CalidadCommon, HttpCase):

    def test_en_vivo_lista_y_vista_de_linea(self):
        """Lista de líneas → vista de línea con el recorrido tipo metro y el bus intercalado → volver."""
        self._viaje_manual()
        codigo = """
            const esperar = (cond, msg) => new Promise((ok, mal) => {
                let n = 0;
                const t = setInterval(() => {
                    if (cond()) { clearInterval(t); ok(); }
                    else if (++n > 150) { clearInterval(t); mal(new Error('No apareció: ' + msg)); }
                }, 100);
            });
            const q = (s) => document.querySelector(s);
            const qa = (s) => document.querySelectorAll(s);
            (async () => {
                const linea = [...qa('.o_ev_linea')].find(e => e.textContent.includes('TCAL-001')
                    || e.textContent.includes('TCAL-002'));
                if (!linea) { throw new Error('La línea con el bus en ruta no aparece'); }
                linea.click();
                await esperar(() => q('.o_ev_linea_cab') && qa('.o_ev_parada').length >= 2
                    && q('.o_ev_tramo_bus') && q('.o_ev_bus_card .o_ev_conf_baja'), 'vista de línea');
                q('.o_ev_volver').click();
                await esperar(() => qa('.o_ev_linea').length >= 3, 'vuelta a la lista');
                q('.o_ev_buscar input').value = 'zzz-no-existe';
                q('.o_ev_buscar input').dispatchEvent(new Event('input'));
                await esperar(() => q('.o_ev_vacio') && !q('.o_ev_linea'), 'búsqueda sin resultados');
                console.log('test successful');
            })().catch(e => console.error(e.message));
        """
        listo = ("[...document.querySelectorAll('.o_ev_linea')].filter(e => e.textContent.includes('TCAL-R'))"
                 ".length === 3 && !!document.querySelector('.o_ev_estado_vivo')")
        self.browser_js('/web#action=transporte_ui.action_en_vivo', codigo, ready=listo, login='admin', timeout=120)
