# -*- coding: utf-8 -*-
"""Pruebas de interfaz (navegador headless): el dashboard y el viaje se renderizan sin errores JS.

Requieren Chromium en el contenedor de Odoo (ver docs/PLAN_PRUEBAS.md). Ejecutar con:
    --test-tags ui/transporte_calidad
"""
from odoo.tests.common import HttpCase, tagged

from .test_calidad import CalidadCommon


@tagged('post_install', '-at_install', '-standard', 'ui')
class TestUiCalidad(CalidadCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        accion = cls.env['transporte.calidad.simulacion'].create({
            'fecha_inicio': cls.ayer, 'dias': 1, 'ruta_ids': [(6, 0, cls.rutas.ids)],
            'vehicle_ids': [(6, 0, (cls.bus1 | cls.bus2).ids)], 'driver_id': cls.conductor.id,
        }).action_generar()
        cls.viajes = cls.env['transporte.viaje'].browse(accion['domain'][0][2])

    def test_dashboard_renderiza_kpis_y_graficos(self):
        """Pestaña «Resumen»: 8 indicadores de transporte y 2 gráficos; fórmulas ocultas hasta pedirlas."""
        listo = ("document.querySelectorAll('.o_cd_kpi').length === 8"
                 " && document.querySelectorAll('.o_calidad_dashboard canvas').length === 2"
                 " && document.querySelectorAll('.o_cd_tab').length === 5"
                 " && !document.querySelector('.o_cd_kpi_formula')")
        self.browser_js('/web#action=transporte_calidad.action_dashboard_calidad',
                        "console.log('test successful')", ready=listo, login='admin', timeout=90)

    def test_dashboard_pestanas_y_formulas(self):
        """Recorre todas las pestañas: cada una muestra su contenido y el mapa se crea solo en «Flota»."""
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
            const tab = (id) => q('.o_cd_tab[data-tab="' + id + '"]').click();
            (async () => {
                [...qa('.o_cd_cabecera button')].find(b => b.textContent.includes('Fórmulas')).click();
                await esperar(() => qa('.o_cd_kpi_formula').length === 8, 'fórmulas visibles');
                tab('flota');
                await esperar(() => q('.o_cd_mapa.leaflet-container') && q('.o_cd_tabla tbody tr'), 'flota y mapa');
                tab('rutas');
                await esperar(() => !q('.leaflet-container') && qa('canvas').length === 1
                    && [...qa('.o_cd_tabla tbody tr')].filter(r => r.textContent.includes('TCAL-R')).length === 3,
                    'rutas y evolución');
                tab('historial');
                await esperar(() => qa('.o_cd_tabla tbody tr.o_cd_click').length > 0, 'historial');
                tab('software');
                await esperar(() => qa('.o_cd_kpi').length === 4 && q('.o_cd_tol'), 'calidad del software');
                tab('resumen');
                await esperar(() => qa('.o_cd_kpi').length === 8 && qa('canvas').length === 2, 'vuelta al resumen');
                console.log('test successful');
            })().catch(e => console.error(e.message));
        """
        self.browser_js('/web#action=transporte_calidad.action_dashboard_calidad', codigo,
                        ready="document.querySelectorAll('.o_cd_kpi').length === 8", login='admin', timeout=120)

    def test_mapa_rutas_renderiza_rutas_e_indicadores(self):
        """El mapa lista las rutas con sus indicadores (el teselado de OSM puede faltar sin Internet)."""
        listo = ("[...document.querySelectorAll('.o_calidad_mapa_rutas .o_cmr_ruta')]"
                 ".filter(e => e.textContent.includes('TCAL-R')).length === 3")
        self.browser_js('/web#action=transporte_calidad.action_mapa_rutas',
                        "console.log('test successful')", ready=listo, login='admin', timeout=90)

    def test_formulario_viaje_muestra_evaluacion(self):
        viaje = self.viajes.filtered(lambda v: v.escenario_simulado == 'atrasado')
        listo = ("!!document.querySelector('.o_form_view .ribbon')"
                 " && [...document.querySelectorAll('.o_notebook .nav-link')]"
                 ".some(e => e.textContent.includes('Evaluación de calidad'))")
        self.browser_js('/web#model=transporte.viaje&id=%s&view_type=form' % viaje.id,
                        "console.log('test successful')", ready=listo, login='admin', timeout=90)

    def test_informe_del_viaje(self):
        """En modo test Odoo entrega el informe como HTML (sin wkhtmltopdf); se valida su contenido."""
        self.authenticate('admin', 'admin')
        viaje = self.viajes.filtered(lambda v: v.escenario_simulado == 'desviacion')
        resp = self.url_open('/report/html/transporte_calidad.informe_viaje/%s' % viaje.id, timeout=120)
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        for esperado in (viaje.name, 'DATOS SIMULADOS', 'Incidencias detectadas', 'Desviación de la ruta',
                         viaje.ruta_id.name):
            self.assertIn(esperado, html)
