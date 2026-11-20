/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, onWillStart, onWillUnmount, useState } from "@odoo/owl";

const REFRESCO_MS = 60000;

/** Pantalla de Inicio de SGM-TB: resumen en vivo y accesos directos según los permisos del usuario. */
export class InicioSgm extends Component {
    static template = "transporte_ui.Inicio";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ datos: null, cargando: false });
        onWillStart(() => this.cargar());
        onMounted(() => {
            this.timer = setInterval(() => this.cargar(), REFRESCO_MS);
        });
        onWillUnmount(() => clearInterval(this.timer));
    }

    async cargar() {
        this.state.cargando = true;
        try {
            this.state.datos = await this.orm.call("transporte.inicio", "get_inicio_data", []);
        } finally {
            this.state.cargando = false;
        }
    }

    // ------------------------------------------------------------------ formato
    pct(valor) {
        return valor === null || valor === undefined ? "—" : `${Number(valor).toFixed(1)} %`;
    }

    min(valor) {
        return valor === null || valor === undefined ? "—" : `${Number(valor).toFixed(1)} min`;
    }

    tono(valor, bueno = 90, regular = 70) {
        if (valor === null || valor === undefined) {
            return "o_sgm_neutro";
        }
        return valor >= bueno ? "o_sgm_bien" : valor >= regular ? "o_sgm_regular" : "o_sgm_mal";
    }

    fechaLarga(iso) {
        const [a, m, d] = iso.split("-").map(Number);
        const texto = new Date(a, m - 1, d).toLocaleDateString("es-EC", {
            weekday: "long", day: "numeric", month: "long", year: "numeric",
        });
        return texto.charAt(0).toUpperCase() + texto.slice(1);
    }

    get maxIncidencias() {
        return Math.max(1, ...this.state.datos.top_incidencias.map((f) => f.n));
    }

    // ------------------------------------------------------------------ navegación
    tieneAcceso(clave) {
        return this.state.datos.accesos.some((a) => a.clave === clave);
    }

    abrir(clave) {
        const acceso = this.state.datos.accesos.find((a) => a.clave === clave);
        if (acceso) {
            this.action.doAction(acceso.accion);
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
}

registry.category("actions").add("transporte_ui_inicio", InicioSgm);
