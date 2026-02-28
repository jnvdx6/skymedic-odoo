# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.http import request
from odoo.addons.iot.controllers.main import IoTController

_logger = logging.getLogger(__name__)


class IoTControllerInherit(IoTController):

    @http.route('/iot/setup', type='jsonrpc', auth='public')
    def update_box(self, iot_box, devices):
        """Override to preserve manually configured IPs (e.g. Tailscale VPN IPs).

        When an IoT Box connects via /iot/setup, it reports its local network IP.
        If we've manually set a Tailscale IP, we don't want it overwritten.
        We detect this by checking if the current IP differs from the reported one
        and the current IP is in the Tailscale range (100.x.x.x).
        """
        iot_identifier = iot_box['identifier']
        box = self._search_box(iot_identifier) or self._search_box(iot_box.get('mac'))

        if box and box.ip and box.ip.startswith('100.'):
            # Preserve the Tailscale IP by injecting it into the incoming data
            reported_ip = iot_box['ip']
            iot_box['ip'] = box.ip
            if reported_ip != box.ip:
                _logger.info(
                    'IoT Box %s reported IP %s, preserving configured Tailscale IP %s',
                    box.name, reported_ip, box.ip
                )

        return super().update_box(iot_box, devices)
