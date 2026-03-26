/** @odoo-module **/

import { UserMenu } from "@web/webclient/user_menu/user_menu";
import { session } from "@web/session";
import { patch } from "@web/core/utils/patch";
import { routeToUrl } from "@web/core/browser/router_service";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
const userMenuRegistry = registry.category("user_menuitems");

patch(UserMenu.prototype, "odoo-debrand-11.UserMenu", {
    setup() {
        this._super.apply(this, arguments);
        userMenuRegistry.remove("documentation");
        userMenuRegistry.remove("support");
        userMenuRegistry.remove("odoo_account");
    },
});
