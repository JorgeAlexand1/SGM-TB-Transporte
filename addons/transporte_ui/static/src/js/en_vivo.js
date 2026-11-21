/** @odoo-module **/
import { registry } from "@web/core/registry";
import { loadCSS, loadJS } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";
import { escape } from "@web/core/utils/strings";
import { Component, onMounted, onWillStart, onWillUnmount, useRef, useState } from "@odoo/owl";

// Leaflet 1.9.4 incluido en transporte_gps_traccar (BSD-2).
const LEAFLET = "/transporte_gps_traccar/static/lib/leaflet";
const REFRESCO_MS = 15000;
const ANIMACION_MS = 1200;
const CENTRO_UTA = [-1.2491, -78.6167];
const MARGEN_LLEGANDO_MIN = 2; // pasado este margen la llegada se muestra como «Esperado HH:MM»

const CONFIANZA = {
    alta: { texto: "GPS en vivo", titulo: "Estimación con la posición GPS actual del bus" },
    media: { texto: "Señal desactualizada", titulo: "El bus dejó de enviar posiciones: la estimación puede fallar" },
    baja: { texto: "Según horario", titulo: "Sin GPS: hora programada más el retraso registrado" },
};
const ESTADO_BUS = {
    a_tiempo: { texto: "A tiempo", clase: "o_ev_ok" },
    retraso: { texto: "Con retraso", clase: "o_ev_tarde" },
    desviado: { texto: "Fuera de ruta", clase: "o_ev_mal" },
};

/** "2026-11-21 14:05:00" (UTC, formato del servidor) → milisegundos. */
function aMs(iso) {
    return Date.parse(iso.replace(" ", "T") + "Z");
}

/**
 * Pantalla «En vivo», inspirada en las apps de transporte público (Moovit):
 * cada ruta es una línea con color, los buses se mueven sobre el mapa y cada parada
 * muestra una cuenta regresiva con un indicador de confianza de la estimación.
 */
export class EnVivoSgm extends Component {
    static template = "transporte_ui.EnVivo";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.mapaRef = useRef("mapa");
        this.map = null;
        this.capasLinea = {};
        this.marcadores = {};
        this.desfase = 0; // reloj del servidor − reloj del navegador
        this.state = useState({
            datos: null,
            lineaId: null,
            viajeId: null,
            buscar: "",
            ahora: Date.now(),
            actualizado: Date.now(),
            sinMapa: false,
        });

        onWillStart(() => this.cargar());
        onMounted(async () => {
            this.reloj = setInterval(() => (this.state.ahora = Date.now()), 1000);
            this.timer = setInterval(() => this.cargar(), REFRESCO_MS);
            try {
                await loadCSS(`${LEAFLET}/leaflet.css`);
                await loadJS(`${LEAFLET}/leaflet.js`);
            } catch {
                this.state.sinMapa = true; // sin Internet: la lista y las cuentas regresivas siguen funcionando
                return;
            }
            this.crearMapa();
        });
        onWillUnmount(() => {
            clearInterval(this.reloj);
            clearInterval(this.timer);
            if (this.map) {
                this.map.remove();
            }
        });
    }

    async cargar() {
        const datos = await this.orm.call("transporte.en.vivo", "get_en_vivo", []);
        this.desfase = aMs(datos.ahora) - Date.now();
        this.state.datos = datos;
        this.state.actualizado = Date.now();
        if (this.state.lineaId && !datos.lineas.some((l) => l.id === this.state.lineaId)) {
            this.state.lineaId = null;
        }
        if (this.map) {
            this.actualizarBuses();
        }
    }

    // ------------------------------------------------------------------ mapa
    crearMapa() {
        this.map = L.map(this.mapaRef.el, { zoomControl: false }).setView(CENTRO_UTA, 13);
        L.control.zoom({ position: "bottomright" }).addTo(this.map);
        L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
            maxZoom: 19,
            subdomains: "abcd",
            attribution: "&copy; OpenStreetMap &copy; CARTO",
        }).addTo(this.map);
        for (const linea of this.state.datos.lineas) {
            this.capasLinea[linea.id] = this.crearCapaLinea(linea).addTo(this.map);
        }
        this.actualizarBuses();
        this.encuadrar(this.state.datos.lineas);
    }

    crearCapaLinea(linea) {
        const capa = L.featureGroup();
        if (linea.trazado.length > 1) {
            // borde blanco + color de la línea, como el trazado de las apps de transporte
            L.polyline(linea.trazado, { color: "#FFFFFF", weight: 9, opacity: 0.9 }).addTo(capa);
            L.polyline(linea.trazado, { color: linea.color, weight: 5, opacity: 0.95 }).addTo(capa);
        }
        for (const p of linea.paradas) {
            L.circleMarker([p.lat, p.lon], {
                radius: 5, color: linea.color, weight: 3, fillColor: "#FFFFFF", fillOpacity: 1,
            })
                .bindTooltip(`${escape(p.nombre)}`, { direction: "top", offset: [0, -4] })
                .on("click", () => this.seleccionarLinea(linea))
                .addTo(capa);
        }
        return capa;
    }

    iconoBus(linea, bus) {
        const vivo = bus.confianza === "alta" ? " o_ev_marca_viva" : "";
        return L.divIcon({
            className: "o_ev_marca_icono",
            html: `<div class="o_ev_marca${vivo}" style="--c:${linea.color}">` +
                `<i class="fa fa-bus"></i><b>${escape(linea.codigo)}</b></div>`,
            iconSize: [58, 30],
            iconAnchor: [29, 15],
        });
    }

    popupBus(linea, bus) {
        const prox = bus.proxima
            ? `Próxima parada: <b>${escape(bus.proxima.nombre)}</b> · ${escape(this.cuenta(bus.proxima.eta))}<br/>`
            : "Llegando al destino<br/>";
        const vel = bus.velocidad === null ? "" : `${Math.round(bus.velocidad)} km/h · `;
        return `<b>${escape(linea.codigo)} · ${escape(bus.bus)}</b><br/>${prox}` +
            `${vel}GPS ${escape(this.hace(bus.fecha_gps))}`;
    }

    /** Crea, mueve (con animación) o quita los marcadores de los buses con posición GPS. */
    actualizarBuses() {
        const vistos = new Set();
        for (const linea of this.state.datos.lineas) {
            for (const bus of linea.buses) {
                if (bus.lat === null) {
                    continue; // sin GPS no se inventa una posición: solo se muestra en la lista
                }
                vistos.add(bus.viaje_id);
                const destino = [bus.lat, bus.lon];
                let m = this.marcadores[bus.viaje_id];
                if (!m) {
                    m = L.marker(destino, { icon: this.iconoBus(linea, bus), zIndexOffset: 1000 })
                        .on("click", () => this.seleccionarLinea(linea, bus))
                        .addTo(this.map);
                    this.marcadores[bus.viaje_id] = m;
                } else {
                    m.setIcon(this.iconoBus(linea, bus));
                    this.deslizar(m, destino);
                }
                m.bindPopup(this.popupBus(linea, bus));
            }
        }
        for (const [id, m] of Object.entries(this.marcadores)) {
            if (!vistos.has(Number(id))) {
                this.map.removeLayer(m);
                delete this.marcadores[id];
            }
        }
        this.resaltar();
    }

    deslizar(marcador, destino) {
        const origen = marcador.getLatLng();
        const inicio = performance.now();
        const paso = (t) => {
            const k = Math.min(1, (t - inicio) / ANIMACION_MS);
            const e = 1 - Math.pow(1 - k, 3);
            marcador.setLatLng([origen.lat + (destino[0] - origen.lat) * e, origen.lng + (destino[1] - origen.lng) * e]);
            if (k < 1) {
                requestAnimationFrame(paso);
            }
        };
        requestAnimationFrame(paso);
    }

    /** Atenúa las demás líneas cuando hay una seleccionada. */
    resaltar() {
        const sel = this.state.lineaId;
        for (const [id, capa] of Object.entries(this.capasLinea)) {
            const activa = !sel || Number(id) === sel;
            capa.setStyle({ opacity: activa ? 0.95 : 0.15, fillOpacity: activa ? 1 : 0.15 });
            if (activa) {
                capa.bringToFront();
            }
        }
    }

    encuadrar(lineas) {
        const puntos = lineas.flatMap((l) => [...l.trazado, ...l.paradas.map((p) => [p.lat, p.lon])]);
        if (this.map && puntos.length) {
            this.map.flyToBounds(puntos, { padding: [40, 40], maxZoom: 16, duration: 0.8 });
        }
    }

    // ------------------------------------------------------------------ acciones
    seleccionarLinea(linea, bus = null) {
        this.state.lineaId = linea.id;
        this.state.viajeId = bus ? bus.viaje_id : (linea.buses[0] && linea.buses[0].viaje_id) || null;
        if (this.map) {
            this.resaltar();
            this.encuadrar([linea]);
        }
    }

    volver() {
        this.state.lineaId = null;
        this.state.viajeId = null;
        if (this.map) {
            this.resaltar();
            this.encuadrar(this.state.datos.lineas);
        }
    }

    seleccionarBus(bus) {
        this.state.viajeId = bus.viaje_id;
        const m = this.marcadores[bus.viaje_id];
        if (m && this.map) {
            this.map.flyTo(m.getLatLng(), 16, { duration: 0.8 });
            m.openPopup();
        }
    }

    verParada(parada) {
        if (this.map && parada.lat !== undefined) {
            this.map.flyTo([parada.lat, parada.lon], 17, { duration: 0.8 });
        }
    }

    abrirViaje(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "transporte.viaje",
            res_id: id,
            views: [[false, "form"]],
        });
    }

    // ------------------------------------------------------------------ datos derivados
    get lineas() {
        const q = this.state.buscar.trim().toLowerCase();
        const lineas = this.state.datos.lineas.filter((l) => !q ||
            [l.codigo, l.nombre, l.origen, l.destino, ...l.paradas.map((p) => p.nombre)]
                .some((t) => (t || "").toLowerCase().includes(q)));
        return [...lineas].sort((a, b) => b.buses.length - a.buses.length);
    }

    get linea() {
        return this.state.datos.lineas.find((l) => l.id === this.state.lineaId);
    }

    get bus() {
        const linea = this.linea;
        return linea && (linea.buses.find((b) => b.viaje_id === this.state.viajeId) || linea.buses[0]);
    }

    /** Filas de la vista de línea: paradas en orden con el bus intercalado en el tramo en que va. */
    get filasLinea() {
        const linea = this.linea;
        const bus = this.bus;
        const coords = Object.fromEntries(linea.paradas.map((p) => [p.secuencia, p]));
        const filas = [];
        const paradas = bus ? bus.paradas : linea.paradas.map((p) => ({ ...p, estado: "plan" }));
        paradas.forEach((p, i) => {
            if (bus && i === bus.tramo + 1) {
                filas.push({ tipo: "bus", clave: "bus" });
            }
            const pasada = bus && i <= bus.tramo;
            filas.push({
                tipo: "parada", clave: `p${p.secuencia}`, ...p, ...(coords[p.secuencia] || {}),
                pasada, proxima: bus && bus.proxima && bus.proxima.secuencia === p.secuencia,
                extremo: i === 0 || i === paradas.length - 1,
            });
        });
        if (bus && bus.tramo + 1 >= paradas.length) {
            filas.push({ tipo: "bus", clave: "bus" });
        }
        return filas;
    }

    resumenLinea(linea) {
        const etas = linea.buses.filter((b) => b.proxima && b.proxima.eta).map((b) => b.proxima.eta).sort();
        if (etas.length) {
            return { tipo: "eta", texto: this.cuenta(etas[0]), etiqueta: "próxima parada" };
        }
        if (linea.salidas.length) {
            return { tipo: "salida", texto: this.horaLocal(linea.salidas[0].hora), etiqueta: "próxima salida" };
        }
        return null;
    }

    // ------------------------------------------------------------------ formato
    minutosHasta(iso) {
        return Math.round((aMs(iso) - (this.state.ahora + this.desfase)) / 60000);
    }

    cuenta(iso) {
        if (!iso) {
            return "—";
        }
        const m = this.minutosHasta(iso);
        if (m < -MARGEN_LLEGANDO_MIN) {
            return `Esperado ${this.horaLocal(iso)}`;
        }
        if (m <= 0) {
            return "Llegando";
        }
        return m < 60 ? `${m} min` : this.horaLocal(iso);
    }

    /** Llegando (parpadea) o vencida (ámbar): la hora estimada ya pasó y el bus no ha llegado. */
    claseEta(iso) {
        const m = this.minutosHasta(iso);
        if (m < -MARGEN_LLEGANDO_MIN) {
            return "o_ev_vencida";
        }
        return m <= 0 ? "o_ev_llegando" : "";
    }

    horaLocal(iso) {
        return iso ? new Date(aMs(iso)).toLocaleTimeString("es-EC", { hour: "2-digit", minute: "2-digit" }) : "—";
    }

    hace(iso) {
        if (!iso) {
            return "sin datos";
        }
        const s = Math.max(0, Math.round((this.state.ahora + this.desfase - aMs(iso)) / 1000));
        if (s < 60) {
            return `hace ${s} s`;
        }
        return s < 3600 ? `hace ${Math.round(s / 60)} min` : `a las ${this.horaLocal(iso)}`;
    }

    get haceActualizado() {
        const s = Math.max(0, Math.round((this.state.ahora - this.state.actualizado) / 1000));
        return s < 5 ? "ahora" : `hace ${s} s`;
    }

    retrasoTexto(min) {
        if (min === null || min === undefined) {
            return "";
        }
        const r = Math.round(min);
        if (r === 0) {
            return "puntual";
        }
        return r > 0 ? `+${r} min` : `${r} min`;
    }

    claseRetraso(min) {
        if (min === null || min === undefined) {
            return "";
        }
        return min > this.state.datos.tolerancia ? "o_ev_tarde" : "o_ev_ok";
    }

    claseParada(f) {
        return [`o_ev_p_${f.estado}`, f.pasada ? "o_ev_pasada" : "", f.proxima ? "o_ev_es_proxima" : "",
            f.extremo ? "o_ev_extremo" : ""].join(" ");
    }

    confianza(clave) {
        return CONFIANZA[clave] || CONFIANZA.baja;
    }

    estadoBus(clave) {
        return ESTADO_BUS[clave] || ESTADO_BUS.a_tiempo;
    }
}

registry.category("actions").add("transporte_ui_en_vivo", EnVivoSgm);
