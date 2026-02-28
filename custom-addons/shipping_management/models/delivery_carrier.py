from odoo import _, fields, models
from odoo.exceptions import UserError


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    # ---- SLA configuration ----

    sla_delivery_days = fields.Integer(
        string="Plazo SLA (días)",
        default=3,
        help="Días máximos de entrega esperados. Pasado este plazo "
        "se genera una alerta automática.",
    )

    # ---- Provider-agnostic dispatch methods ----

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
            _("Reimpresión de etiquetas no soportada para %s.") % self.name
        )

    def _generate_return_shipment(self, shipment):
        """Provider-agnostic interface for generating a return shipment.

        Delivery provider modules should implement:
            _<delivery_type>_generate_return_shipment(shipment)

        Returns a dict with at least 'tracking_ref' key.
        Falls back to the standard get_return_label pattern if available.
        """
        self.ensure_one()
        # Try shipping_management-specific method first
        method_name = f"_{self.delivery_type}_generate_return_shipment"
        if hasattr(self, method_name):
            return getattr(self, method_name)(shipment)

        # Fallback: try existing get_return_label on picking
        fallback_name = f"{self.delivery_type}_get_return_label"
        if shipment.picking_id and hasattr(self, fallback_name):
            tracking_ref = getattr(self, fallback_name)(shipment.picking_id)
            return {
                "tracking_ref": tracking_ref if isinstance(tracking_ref, str) else False,
                "expedition_code": False,
            }

        raise UserError(
            _("Gestión de devoluciones no soportada para %s.") % self.name
        )
