/** @odoo-module **/
import { registry } from "@web/core/registry";
import { loadCSS, loadJS } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";
import { escape } from "@web/core/utils/strings";
import { Component, onMounted, onWillStart, onWillUnmount, useRef, useState } from "@odoo/owl";

// Leaflet 1.9.4 incluido en el módulo (BSD-2): los mapas funcionan sin acceso al CDN.
const LEAFLET = "/transporte_gps_traccar/static/lib/leaflet";
const COLORES = ["#0d6efd", "#198754", "#fd7e14", "#6f42c1", "#dc3545", "#20c997", "#6c757d"];

/**
 * Mapa de rutas: trazado de referencia (o línea de paradas) usado para detectar desvíos,
 * paradas con su radio de detección e indicadores históricos de cumplimiento por ruta.
 */
export class MapaRutas extends Component {
    static template = "transporte_calidad.MapaRutas";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.mapaRef = useRef("mapa");
        this.map = null;
        this.capas = {};
        this.state = useState({ rutas: [], visibles: {}, sinMapa: false });

        onWillStart(async () => {
            const rutas = await this.orm.call("transporte.ruta", "get_mapa_rutas", []);
            rutas.forEach((r, i) => {
                r.color = COLORES[i % COLORES.length];
                this.state.visibles[r.id] = true;
            });
            this.state.rutas = rutas;
        });
        onMounted(async () => {
            try {
                await loadCSS(`${LEAFLET}/leaflet.css`);
                await loadJS(`${LEAFLET}/leaflet.js`);
            } catch {
                this.state.sinMapa = true; // sin Internet: se mantiene la tabla de indicadores
                return;
            }
            this.map = L.map(this.mapaRef.el).setView([-1.2491, -78.6167], 13);
            L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
                maxZoom: 19,
                attribution: "&copy; OpenStreetMap",
            }).addTo(this.map);
            for (const r of this.state.rutas) {
                this.capas[r.id] = this.crearCapa(r).addTo(this.map);
            }
            this.ajustar(this.state.rutas);
        });
        onWillUnmount(() => {
            if (this.map) {
                this.map.remove();
            }
        });
    }

    crearCapa(r) {
        const capa = L.layerGroup();
        if (r.trazado.length > 1) {
            L.polyline(r.trazado, {
                color: r.color,
                weight: 5,
                opacity: 0.85,
                dashArray: r.trazado_real ? null : "8 8",
            })
                .bindPopup(
                    `<b>${escape(r.codigo)} · ${escape(r.nombre)}</b><br/>` +
                        `${r.trazado_real ? "Trazado de referencia" : "Línea entre paradas (sin trazado)"}<br/>` +
                        `Corredor permitido: ${r.corredor} m<br/>` +
                        `${r.distancia.toFixed(2)} km · ${r.tiempo} min`
                )
                .addTo(capa);
        }
        for (const p of r.paradas) {
            L.circle([p.lat, p.lon], { radius: p.radio, color: r.color, weight: 1, fillOpacity: 0.12 }).addTo(capa);
            L.circleMarker([p.lat, p.lon], { radius: 6, color: "#000", weight: 1, fillColor: r.color, fillOpacity: 1 })
                .bindPopup(`<b>${p.secuencia}. ${escape(p.nombre)}</b><br/>${escape(r.codigo)} · minuto ${p.min}<br/>Radio ${p.radio} m`)
                .addTo(capa);
        }
        return capa;
    }

    puntos(rutas) {
        return rutas.flatMap((r) => [...r.trazado, ...r.paradas.map((p) => [p.lat, p.lon])]);
    }

    ajustar(rutas) {
        const puntos = this.puntos(rutas);
        if (this.map && puntos.length) {
            this.map.fitBounds(puntos, { padding: [30, 30], maxZoom: 16 });
        }
    }

    // ------------------------------------------------------------------ acciones
    alternar(r) {
        const visible = !this.state.visibles[r.id];
        this.state.visibles[r.id] = visible;
        const capa = this.capas[r.id];
        if (this.map && capa) {
            if (visible) {
                capa.addTo(this.map);
            } else {
                this.map.removeLayer(capa);
            }
        }
    }

    enfocar(r) {
        if (!this.state.visibles[r.id]) {
            this.alternar(r);
        }
        this.ajustar([r]);
    }

    abrirRuta(r) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "transporte.ruta",
            res_id: r.id,
            views: [[false, "form"]],
        });
    }

    claseIndicador(valor, evaluados) {
        if (!evaluados) {
            return "text-muted";
        }
        if (valor >= 90) {
            return "text-success";
        }
        return valor >= 70 ? "text-warning" : "text-danger";
    }
}

registry.category("actions").add("transporte_calidad_mapa_rutas", MapaRutas);
