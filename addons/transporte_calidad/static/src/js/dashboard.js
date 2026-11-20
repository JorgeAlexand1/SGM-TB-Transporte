/** @odoo-module **/
import { registry } from "@web/core/registry";
import { loadCSS, loadJS } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";
import { deserializeDateTime, formatDateTime } from "@web/core/l10n/dates";
import { Component, onMounted, onWillStart, onWillUnmount, useRef, useState } from "@odoo/owl";

// Leaflet 1.9.4 incluido en el módulo (BSD-2): los mapas funcionan sin acceso al CDN.
const LEAFLET = "/transporte_gps_traccar/static/lib/leaflet";
const COLORES = ["#0d6efd", "#198754", "#fd7e14", "#6f42c1", "#dc3545", "#20c997", "#6c757d"];

export class CalidadDashboard extends Component {
    static template = "transporte_calidad.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.refs = {
            rutas: useRef("chartRutas"),
            periodos: useRef("chartPeriodos"),
            pareto: useRef("chartPareto"),
            mapa: useRef("mapa"),
        };
        this.charts = {};
        this.map = null;
        this.capa = null;
        this.state = useState({ datos: null, cargando: true, filtros: { datos: "todos" } });

        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");
            await this.cargar(true);
        });
        onMounted(async () => {
            this.dibujar();
            try {
                await loadCSS(`${LEAFLET}/leaflet.css`);
                await loadJS(`${LEAFLET}/leaflet.js`);
                this.map = L.map(this.refs.mapa.el).setView([-1.2491, -78.6167], 13);
                L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
                    maxZoom: 19,
                    attribution: "&copy; OpenStreetMap",
                }).addTo(this.map);
                this.capa = L.layerGroup().addTo(this.map);
                this.dibujarMapa(true);
            } catch {
                // sin Internet: el resto del dashboard sigue funcionando
            }
            this.timer = setInterval(() => this.cargar(false).then(() => this.dibujar()), 30000);
        });
        onWillUnmount(() => {
            clearInterval(this.timer);
            Object.values(this.charts).forEach((c) => c.destroy());
            if (this.map) {
                this.map.remove();
            }
        });
    }

    // ------------------------------------------------------------------ datos
    async cargar(registrar) {
        this.state.cargando = true;
        const filtros = Object.assign({}, this.state.filtros, { registrar });
        this.state.datos = await this.orm.call("transporte.calidad.dashboard", "get_dashboard_data", [filtros]);
        this.state.filtros = Object.assign({}, this.state.datos.filtros);
        this.state.cargando = false;
    }

    async aplicarFiltro(campo, ev) {
        const valor = ev.target.value;
        this.state.filtros[campo] = ["ruta_id", "vehicle_id"].includes(campo) ? parseInt(valor) || false : valor;
        await this.cargar(true);
        this.dibujar();
    }

    // ------------------------------------------------------------------ formato
    fmt(valor, sufijo = "", decimales = 1) {
        if (valor === null || valor === undefined || valor === false) {
            return "—";
        }
        return `${Number(valor).toFixed(decimales)}${sufijo}`;
    }

    fecha(texto) {
        return texto ? formatDateTime(deserializeDateTime(texto)) : "—";
    }

    semaforo(valor, tipo = "pct") {
        if (valor === null || valor === undefined) {
            return "o_sem_gris";
        }
        if (tipo === "pct") {
            return valor >= 85 ? "o_sem_verde" : valor >= 70 ? "o_sem_amarillo" : "o_sem_rojo";
        }
        const tol = this.state.datos.tolerancias.retraso_min;
        return valor <= tol ? "o_sem_verde" : valor <= 2 * tol ? "o_sem_amarillo" : "o_sem_rojo";
    }

    get kpisTransporte() {
        const t = this.state.datos.transporte;
        const tol = this.state.datos.tolerancias;
        return [
            {
                titulo: "Cumplimiento de rutas", valor: this.fmt(t.cumplimiento_rutas.valor, " %"),
                clase: this.semaforo(t.cumplimiento_rutas.valor),
                detalle: `${t.cumplimiento_rutas.num ?? 0} de ${t.cumplimiento_rutas.den} viajes completos, sin paradas omitidas ni desvío`,
                formula: "viajes que cumplen la ruta / viajes evaluados × 100",
            },
            {
                titulo: "Puntualidad (paradas)", valor: this.fmt(t.puntualidad_paradas.valor, " %"),
                clase: this.semaforo(t.puntualidad_paradas.valor),
                detalle: `${t.puntualidad_paradas.num} de ${t.puntualidad_paradas.den} llegadas en [-${tol.adelanto_min}, +${tol.retraso_min}] min · viajes puntuales: ${this.fmt(t.puntualidad_viajes.valor, " %")}`,
                formula: "paradas puntuales / paradas visitadas × 100",
            },
            {
                titulo: "Retraso promedio", valor: this.fmt(t.retraso_promedio.valor, " min"),
                clase: this.semaforo(t.retraso_promedio.valor, "min"),
                detalle: `promedio por viaje de max(0, llegada real − programada) en ${t.retraso_promedio.den} viajes`,
                formula: "Σ retraso promedio por viaje / nº viajes",
            },
            {
                titulo: "Paradas cumplidas", valor: this.fmt(t.paradas_cumplidas.valor, " %"),
                clase: this.semaforo(t.paradas_cumplidas.valor),
                detalle: `${t.paradas_cumplidas.num} de ${t.paradas_cumplidas.den} paradas programadas visitadas`,
                formula: "paradas visitadas / paradas programadas × 100",
            },
            {
                titulo: "Desviación de la ruta", valor: this.fmt(t.desviacion_ruta.valor, " %"),
                clase: t.desviacion_ruta.viajes_desviados ? "o_sem_rojo" : "o_sem_verde",
                detalle: `posiciones fuera del corredor · ${t.desviacion_ruta.viajes_desviados} de ${t.desviacion_ruta.den} viajes desviados · máx. ${this.fmt(t.desviacion_ruta.max_m, " m", 0)}`,
                formula: "promedio del % de posiciones a más del corredor permitido",
            },
            {
                titulo: "Distancia estimada vs recorrida", valor: this.fmt(t.diferencia_distancia.valor, " %"),
                clase: "o_sem_gris",
                detalle: `diferencia media ${this.fmt(t.diferencia_distancia.km, " km", 2)} en ${t.diferencia_distancia.den} viajes con GPS`,
                formula: "(recorrida − estimada) / estimada × 100",
            },
            {
                titulo: "Tiempo promedio de recorrido", valor: this.fmt(t.tiempo_promedio.valor, " min"),
                clase: "o_sem_gris",
                detalle: `estimado ${this.fmt(t.tiempo_promedio.estimado, " min")} · ${t.tiempo_promedio.den} viajes completos`,
                formula: "Σ (llegada a destino − salida real) / nº viajes completos",
            },
            {
                titulo: "Incidencias", valor: this.fmt(t.incidencias.valor, "", 0),
                clase: t.incidencias.valor ? "o_sem_amarillo" : "o_sem_verde",
                detalle: `${this.fmt(t.incidencias.por_100_viajes, "", 1)} por cada 100 viajes · ${this.fmt(t.incidencias.por_dia, "", 2)} por día`,
                formula: "conteo en el periodo; frecuencia = n / viajes × 100 y n / días",
            },
        ];
    }

    get kpisSoftware() {
        const s = this.state.datos.software;
        return [
            {
                titulo: "Integridad de registros GPS", valor: this.fmt(s.integridad_gps.valor, " %"),
                clase: this.semaforo(s.integridad_gps.valor),
                detalle: `${s.integridad_gps.num} válidas de ${s.integridad_gps.den} · ${s.integridad_gps.duplicados_descartados} duplicados descartados`,
                formula: "posiciones válidas / posiciones almacenadas × 100",
            },
            {
                titulo: "Exactitud Traccar ↔ Odoo", valor: this.fmt(s.exactitud_sync.valor, " %"),
                clase: this.semaforo(s.exactitud_sync.valor),
                detalle: s.exactitud_sync.fecha
                    ? `muestra de ${s.exactitud_sync.muestra} posiciones (${this.fecha(s.exactitud_sync.fecha)}) · sync OK ${this.fmt(s.exactitud_sync.sync_ok, " %")} de ${s.exactitud_sync.syncs}`
                    : "pulse «Verificar exactitud» para comparar contra Traccar",
                formula: "posiciones idénticas en ambos sistemas / verificadas × 100",
            },
            {
                titulo: "Tiempo de respuesta", valor: this.fmt(s.tiempo_respuesta.valor, " ms", 0),
                clase: s.tiempo_respuesta.p95 === null ? "o_sem_gris" : s.tiempo_respuesta.p95 <= 2000 ? "o_sem_verde" : "o_sem_rojo",
                detalle: `p95 ${this.fmt(s.tiempo_respuesta.p95, " ms", 0)} (${s.tiempo_respuesta.mediciones} mediciones, 30 días) · este cálculo ${this.state.datos.calculo_ms} ms · sync ${this.fmt(s.tiempo_respuesta.sync_ms, " ms", 0)}`,
                formula: "promedio y percentil 95 de las mediciones registradas",
            },
            {
                titulo: "Detección correcta de incidencias", valor: this.fmt(s.deteccion_correcta.valor, " %"),
                clase: this.semaforo(s.deteccion_correcta.valor),
                detalle: `${s.deteccion_correcta.num} de ${s.deteccion_correcta.den} recorridos de prueba con exactamente las incidencias esperadas`,
                formula: "recorridos con detección = esperado / recorridos con escenario × 100",
            },
        ];
    }

    // ------------------------------------------------------------------ gráficos
    grafico(clave, ref, config) {
        if (this.charts[clave]) {
            this.charts[clave].destroy();
        }
        if (ref.el) {
            this.charts[clave] = new Chart(ref.el, config);
        }
    }

    dibujar() {
        const d = this.state.datos;
        if (!d) {
            return;
        }
        const pct = { yAxes: [{ ticks: { beginAtZero: true, max: 100 } }] };
        this.grafico("rutas", this.refs.rutas, {
            type: "bar",
            data: {
                labels: d.rutas.map((r) => r.codigo),
                datasets: [
                    { label: "% cumplimiento", backgroundColor: COLORES[0], data: d.rutas.map((r) => r.cumplimiento) },
                    { label: "% puntualidad", backgroundColor: COLORES[1], data: d.rutas.map((r) => r.puntualidad) },
                    { label: "% paradas cumplidas", backgroundColor: COLORES[2], data: d.rutas.map((r) => r.paradas_cumplidas) },
                ],
            },
            options: { responsive: true, maintainAspectRatio: false, scales: pct },
        });
        this.grafico("periodos", this.refs.periodos, {
            type: "bar",
            data: {
                labels: d.periodos.filas.map((p) => p.periodo),
                datasets: [
                    { type: "line", label: "% cumplimiento", borderColor: COLORES[0], fill: false, yAxisID: "pct", data: d.periodos.filas.map((p) => p.cumplimiento) },
                    { type: "line", label: "% puntualidad", borderColor: COLORES[1], fill: false, yAxisID: "pct", data: d.periodos.filas.map((p) => p.puntualidad) },
                    { label: "Retraso promedio (min)", backgroundColor: "rgba(220,53,69,.5)", yAxisID: "min", data: d.periodos.filas.map((p) => p.retraso_promedio) },
                ],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                scales: {
                    yAxes: [
                        { id: "pct", position: "left", ticks: { beginAtZero: true, max: 100 } },
                        { id: "min", position: "right", ticks: { beginAtZero: true }, gridLines: { drawOnChartArea: false } },
                    ],
                },
            },
        });
        const p = d.transporte.incidencias.por_tipo;
        this.grafico("pareto", this.refs.pareto, {
            type: "bar",
            data: {
                labels: p.map((f) => f.categoria),
                datasets: [
                    { type: "line", label: "% acumulado", borderColor: COLORES[4], fill: false, yAxisID: "acum", data: p.map((f) => f.pct_acumulado) },
                    { label: "Incidencias", backgroundColor: COLORES[3], yAxisID: "n", data: p.map((f) => f.n) },
                ],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                scales: {
                    yAxes: [
                        { id: "n", position: "left", ticks: { beginAtZero: true, precision: 0 } },
                        { id: "acum", position: "right", ticks: { beginAtZero: true, max: 100 }, gridLines: { drawOnChartArea: false } },
                    ],
                },
            },
        });
        this.dibujarMapa(false);
    }

    dibujarMapa(ajustar) {
        if (!this.map || !this.capa || !this.state.datos) {
            return;
        }
        this.capa.clearLayers();
        const puntos = [];
        for (const v of this.state.datos.vehiculos) {
            if (v.lat === null) {
                continue;
            }
            const color = v.senal === "con_senal" ? "#198754" : "#dc3545";
            const viaje = v.viaje ? `<br/>${v.viaje.ruta}<br/>Paradas ${v.viaje.visitadas}/${v.viaje.total} · retraso ${v.viaje.retraso} min` : "";
            L.circleMarker([v.lat, v.lon], { radius: 9, color: "#000", weight: 2, fillColor: color, fillOpacity: 1 })
                .bindPopup(`<b>${v.nombre}</b><br/>${this.fecha(v.fecha)} · ${v.velocidad} km/h${viaje}`)
                .addTo(this.capa);
            puntos.push([v.lat, v.lon]);
        }
        if (ajustar && puntos.length) {
            this.map.fitBounds(puntos, { padding: [30, 30], maxZoom: 16 });
        }
    }

    // ------------------------------------------------------------------ acciones
    abrirViaje(id) {
        this.action.doAction({ type: "ir.actions.act_window", res_model: "transporte.viaje", res_id: id, views: [[false, "form"]] });
    }

    abrirMapaViaje(id) {
        this.action.doAction({ type: "ir.actions.client", tag: "transporte_gps_map", name: "Mapa GPS", context: { viaje_id: id } });
    }

    abrirIncidencias() {
        this.action.doAction("transporte_calidad.action_incidencia");
    }

    async verificarExactitud() {
        try {
            const accion = await this.orm.call("transporte.calidad.dashboard", "action_verificar_exactitud", []);
            await this.action.doAction(accion);
            await this.cargar(false);
            this.dibujar();
        } catch (e) {
            this.notification.add(e.data?.message || e.message || String(e), { type: "danger" });
        }
    }
}

registry.category("actions").add("transporte_calidad_dashboard", CalidadDashboard);
