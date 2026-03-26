/** @odoo-module **/

import { WebClient } from "@web/webclient/webclient";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
const { onWillStart } = owl;

patch(WebClient.prototype, "odoo-debrand-11.WebClient", {
    setup() {
        this._super.apply(this, arguments);
        this.title.setParts({ zopenerp: "" });
    },
    async willStart() {
        // Fetch from ORM
        this.orm = useService("orm");
        const com = await this.orm.call('res.company', 'get_current_company', []);
        const args = {
            domain: [['id', '=', com]],
            fields: ["brand_name", "name"],
            context: [],
        }
        const res = await this.orm.call('res.company', 'search_read', [], args);
        this.brandName = res && res[0].brand_name;
        this.CompanyName = res && res[0].name;
        const brand_name = this.brandName || this.CompanyName;
        this.title.setParts({ zopenerp: brand_name }); // :)
    },
});

patch(Dialog.prototype, "odoo-debrand-11.Dialog", {
    setup() {
        this._super.apply(this, arguments);
        this.title = this.title && this.title.replace(new RegExp("Odoo", "g"), "");
        this.constructor.title = this.constructor.title &&  this.constructor.title.replace(new RegExp("Odoo", "g"), "");
    },
});

// Remove Odoo Caption From Title
Dialog.title  = Dialog.title && Dialog.title.replace(new RegExp("Odoo", "g"), "");

import { NotificationRequest } from "@mail/components/notification_request/notification_request";

patch (NotificationRequest.prototype, 'odoo-debrand-11.notificationExtend', {setup() {
        this._super.apply(this, arguments);
        },
        _handleResponseNotificationPermission(value) {
            this.messaging.refreshIsNotificationPermissionDefault();
            if (value !== 'granted') {
                this.messaging.userNotificationManager.sendNotification({
                    message: this.env._t("System will not have the permission to send native notifications on this device."),
                    title: this.env._t("Permission denied"),
                });
            }
        }
});