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
        listo = ("document.querySelectorAll('.o_cd_kpi').length === 12"
                 " && document.querySelectorAll('.o_calidad_dashboard canvas').length === 3"
                 " && !!document.querySelector('.o_cd_panel table tbody tr')")
        self.browser_js('/web#action=transporte_calidad.action_dashboard_calidad',
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
