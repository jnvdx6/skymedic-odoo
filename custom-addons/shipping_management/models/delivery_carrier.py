from odoo import _, models
from odoo.exceptions import UserError


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    def _update_shipment_status(self, shipment):
        """Provider-agnostic interface for updating a shipping.shipment status.

        Delivery provider modules should implement:
            _<delivery_type>_update_shipment_status(shipment)

        The method should:
        1. Query the carrier API for tracking info.
        2. Update shipment.tracking_status_raw with the raw response.
        3. Optionally update shipment.state if the status can be mapped.
        4. Post a message to the shipment chatter.
        """
        self.ensure_one()
        method_name = f"_{self.delivery_type}_update_shipment_status"
        if hasattr(self, method_name):
            return getattr(self, method_name)(shipment)
        return False

    def _reprint_shipment_label(self, shipment):
        """Provider-agnostic interface for reprinting a shipment label.

        Delivery provider modules should implement:
            _<delivery_type>_reprint_shipment_label(shipment)
        """
        self.ensure_one()
        method_name = f"_{self.delivery_type}_reprint_shipment_label"
        if hasattr(self, method_name):
            return getattr(self, method_name)(shipment)
        raise UserError(
            _("Reimpresión de etiquetas no soportada para %s.")
            % self.name
        )
