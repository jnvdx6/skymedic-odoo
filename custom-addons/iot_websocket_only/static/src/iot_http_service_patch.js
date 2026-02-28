/** @odoo-module **/
import { IotHttpService } from "@iot/network_utils/iot_http_service";
import { patch } from "@web/core/utils/patch";

/**
 * Force IoT communication to use only the websocket protocol.
 *
 * By default, Odoo tries WebRTC → Longpolling (direct HTTP) → Websocket.
 * WebRTC and Longpolling require the browser to reach the IoT Box IP directly,
 * which fails when the IoT Box is on a VPN (Tailscale) that the browser
 * doesn't have access to.
 *
 * The websocket protocol routes all traffic through the Odoo server's bus.bus
 * channel, so only the server needs to reach the IoT Box.
 */
patch(IotHttpService.prototype, {
    setup() {
        super.setup(...arguments);
        this.connectionTypes = [this._websocket.bind(this)];
        this.connectionStatus = "websocket";
    },
});
