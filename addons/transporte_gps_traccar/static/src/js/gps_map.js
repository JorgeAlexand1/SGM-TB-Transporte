/** @odoo-module **/
import { registry } from "@web/core/registry";
import { loadCSS, loadJS } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, onWillUnmount, useRef } from "@odoo/owl";

const LEAFLET = "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist";
const COLOR_PARADA = { atendida: "#198754", omitida: "#dc3545", pendiente: "#6c757d" };

export class GpsMap extends Component {
    static template = "transporte_gps_traccar.GpsMap";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.mapRef = useRef("map");
        this.viajeId = (this.props.action.context || {}).viaje_id || false;
        this.map = null;
        this.layer = null;
        this.timer = null;
        onMounted(async () => {
            await loadCSS(`${LEAFLET}/leaflet.css`);
            await loadJS(`${LEAFLET}/leaflet.js`);
            this.map = L.map(this.mapRef.el).setView([-1.2491, -78.6167], 13);
            L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
                maxZoom: 19,
                attribution: "&copy; OpenStreetMap",
            }).addTo(this.map);
            this.layer = L.layerGroup().addTo(this.map);
            await this.refresh(true);
            this.timer = setInterval(() => this.refresh(false), 15000);
        });
        onWillUnmount(() => {
            clearInterval(this.timer);
            if (this.map) {
                this.map.remove();
            }
        });
    }

    async refresh(fit) {
        const datos = await this.orm.call("fleet.vehicle", "get_datos_mapa", [this.viajeId]);
        this.layer.clearLayers();
        const puntos = [];
        if (datos.trazado.length) {
            L.polyline(datos.trazado, { color: "#0d6efd", weight: 4 }).addTo(this.layer);
            puntos.push(...datos.trazado);
        }
        for (const p of datos.paradas) {
            const color = COLOR_PARADA[p.estado] || "#6c757d";
            L.circle([p.lat, p.lon], { radius: p.radio, color, fillOpacity: 0.15 }).addTo(this.layer);
            L.circleMarker([p.lat, p.lon], { radius: 6, color, fillColor: color, fillOpacity: 1 })
                .bindPopup(`<b>${p.secuencia}. ${p.nombre}</b><br/>${p.estado}`)
                .addTo(this.layer);
            puntos.push([p.lat, p.lon]);
        }
        for (const v of datos.vehiculos) {
            const color = v.senal === "con_senal" ? "#198754" : "#dc3545";
            L.circleMarker([v.lat, v.lon], { radius: 9, color: "#000", weight: 2, fillColor: color, fillOpacity: 1 })
                .bindPopup(
                    `<b>${v.nombre}</b> ${v.placa}<br/>${v.velocidad} km/h<br/>${v.fecha} UTC<br/>${v.senal}`
                )
                .addTo(this.layer);
            puntos.push([v.lat, v.lon]);
        }
        if (fit && puntos.length) {
            this.map.fitBounds(puntos, { padding: [30, 30], maxZoom: 17 });
        }
    }
}

registry.category("actions").add("transporte_gps_map", GpsMap);
