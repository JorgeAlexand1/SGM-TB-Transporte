# -*- coding: utf-8 -*-
"""Pruebas de la interfaz SGM-TB: datos de la pantalla de Inicio, accesos por rol, menú y login."""
from odoo import fields
from odoo.tests.common import HttpCase, new_test_user, tagged

from odoo.addons.transporte_calidad.tests.test_calidad import CalidadCommon


@tagged('post_install', '-at_install')
class TestInicio(CalidadCommon):

    def test_inicio_coincide_con_registros(self):
        self._wizard().action_generar()
        en_curso = self._viaje_manual(salida=self._salida(22))
        d = self.env['transporte.inicio'].get_inicio_data()
        hoy = fields.Date.context_today(self.env.user)
        Viaje = self.env['transporte.viaje']
        evaluados = Viaje.search_count([('fecha_viaje', '>=', d['periodo']['desde']), ('fecha_viaje', '<=', hoy),
                                        ('resultado', 'in', ('cumple', 'incumple'))])
        self.assertEqual(d['evaluados'], evaluados)
        self.assertGreater(d['simulados'], 0)
        self.assertEqual(d['kpis']['viajes_hoy'], Viaje.search_count([('fecha_viaje', '=', hoy)]))
        self.assertEqual(d['kpis']['incidencias_abiertas'], self.env['transporte.incidencia'].search_count(
            [('estado', 'in', ('abierta', 'en_atencion'))]))
        self.assertIn(en_curso.id, [v['viaje_id'] for v in d['en_ruta']])
        self.assertEqual(d['kpis']['en_ruta'], len(d['en_ruta']))
        # mismos valores que el dashboard para el mismo período
        dash = self.env['transporte.calidad.dashboard'].get_dashboard_data(
            {'fecha_desde': d['periodo']['desde'], 'fecha_hasta': d['periodo']['hasta']})
        self.assertEqual(d['kpis']['cumplimiento'], dash['transporte']['cumplimiento_rutas']['valor'])
        self.assertEqual(d['kpis']['puntualidad'], dash['transporte']['puntualidad_paradas']['valor'])
        self.assertLessEqual(len(d['top_incidencias']), 4)

    def test_accesos_segun_rol(self):
        consulta = new_test_user(self.env, login='tui_consulta', groups='transporte_core.group_transporte_user')
        claves = {a['clave'] for a in self.env['transporte.inicio'].with_user(consulta).get_inicio_data()['accesos']}
        self.assertIn('dashboard', claves)
        self.assertIn('mapa_rutas', claves)
        self.assertNotIn('simulacion', claves)  # solo responsables
        jefe = new_test_user(self.env, login='tui_jefe', groups='transporte_core.group_transporte_manager')
        claves = {a['clave'] for a in self.env['transporte.inicio'].with_user(jefe).get_inicio_data()['accesos']}
        self.assertIn('simulacion', claves)
        for acceso in self.env['transporte.inicio'].get_inicio_data()['accesos']:
            self.assertTrue(self.env.ref(acceso['accion']))

    def test_accesos_principales(self):
        """Inicio muestra 6 tarjetas; el resto de accesos queda en el menú (no se pierde ninguno)."""
        accesos = self.env['transporte.inicio'].get_inicio_data()['accesos']
        principales = [a['clave'] for a in accesos if a['principal']]
        self.assertEqual(principales, ['en_vivo', 'dashboard', 'mapa_rutas', 'viajes', 'incidencias', 'rutas'])
        self.assertGreater(len(accesos), len(principales))

    def test_menu_raiz_abre_inicio(self):
        raiz = self.env.ref('transporte_core.menu_transporte_root')
        self.assertEqual(raiz.action, self.env.ref('transporte_ui.action_inicio'))
        self.assertTrue(raiz.web_icon_data)
        self.assertEqual(self.env.ref('transporte_ui.menu_inicio').parent_id, raiz)


@tagged('post_install', '-at_install')
class TestLogin(HttpCase):

    def test_login_con_marca_propia(self):
        resp = self.url_open('/web/login')
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        for esperado in ('SGM-TB', 'Iniciar sesión', 'o_sgm_login', '/transporte_ui/static/img/favicon.svg'):
            self.assertIn(esperado, html)
        self.assertNotIn('Powered by', html)


@tagged('post_install', '-at_install', '-standard', 'ui')
class TestUiInicio(CalidadCommon, HttpCase):

    def test_inicio_renderiza(self):
        self._wizard().action_generar()
        listo = ("document.querySelectorAll('.o_sgm_inicio .o_sgm_kpi').length === 4"
                 " && document.querySelectorAll('.o_sgm_inicio .o_sgm_mini').length === 4"
                 " && document.querySelectorAll('.o_sgm_inicio .o_sgm_acceso').length === 6"
                 " && document.title.includes('SGM-TB')")
        self.browser_js('/web#action=transporte_ui.action_inicio', "console.log('test successful')",
                        ready=listo, login='admin', timeout=90)
