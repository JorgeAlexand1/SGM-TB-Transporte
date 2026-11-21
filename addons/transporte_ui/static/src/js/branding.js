/** @odoo-module **/
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { WebClient } from "@web/webclient/webclient";
// Importarlo garantiza que sus entradas ya están registradas antes de quitarlas.
import { preferencesItem } from "@web/webclient/user_menu/user_menu_items"; // eslint-disable-line no-unused-vars

// Título de la pestaña: «… - SGM-TB» en lugar de «… - Odoo».
patch(WebClient.prototype, "transporte_ui.WebClient", {
    setup() {
        this._super(...arguments);
        this.title.setParts({ zopenerp: "SGM-TB" });
    },
});

// El menú de usuario no enlaza a la documentación, soporte ni cuenta de odoo.com.
const userMenu = registry.category("user_menuitems");
for (const clave of ["documentation", "support", "odoo_account"]) {
    if (userMenu.contains(clave)) {
        userMenu.remove(clave);
    }
}
