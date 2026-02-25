import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    shipment_ids = fields.One2many(
        "shipping.shipment",
        "picking_id",
        string="Envíos",
    )
    shipment_count = fields.Integer(
        compute="_compute_shipment_count",
        string="Envíos",
    )

    def _compute_shipment_count(self):
        for picking in self:
            picking.shipment_count = len(picking.shipment_ids)

    def send_to_shipper(self):
        """Override to auto-create shipping.shipment after sending."""
        res = super().send_to_shipper()
        self._create_shipping_shipment()
        return res

    def _create_shipping_shipment(self):
        """Create a shipping.shipment record linked to this picking."""
        self.ensure_one()
        if not self.carrier_id or not self.carrier_tracking_ref:
            return False
        # Avoid duplicates
        existing = self.env["shipping.shipment"].search([
            ("picking_id", "=", self.id),
            ("tracking_ref", "=", self.carrier_tracking_ref),
        ], limit=1)
        if existing:
            return existing

        vals = self._prepare_shipment_vals()
        shipment = self.env["shipping.shipment"].create(vals)
        _logger.info(
            "Auto-created shipment %s for picking %s",
            shipment.name,
            self.name,
        )
        self._link_labels_to_shipment(shipment)
        return shipment

    def _prepare_shipment_vals(self):
        """Prepare values for creating a shipping.shipment."""
        self.ensure_one()
        vals = {
            "picking_id": self.id,
            "carrier_id": self.carrier_id.id,
            "tracking_ref": self.carrier_tracking_ref,
            "state": "confirmed",
            "ship_date": fields.Datetime.now(),
            "shipping_cost": self.carrier_price,
            "number_of_packages": getattr(self, "number_of_packages", 1)
            or 1,
        }
        # Copy carrier-specific expedition code if available
        if hasattr(self, "nacex_expedition_code") and self.nacex_expedition_code:
            vals["expedition_code"] = self.nacex_expedition_code
        return vals

    def _link_labels_to_shipment(self, shipment):
        """Find label PDFs from picking and create shipping.label records."""
        self.ensure_one()
        tracking = self.carrier_tracking_ref or ""
        # Search for PDF labels attached to this picking matching the
        # tracking reference or created today
        domain = [
            ("res_model", "=", "stock.picking"),
            ("res_id", "=", self.id),
            ("mimetype", "=", "application/pdf"),
        ]
        if tracking:
            domain.append(("name", "=like", f"{tracking}%"))

        attachments = self.env["ir.attachment"].search(domain)
        if not attachments and tracking:
            # Fallback: any PDF created today on this picking
            attachments = self.env["ir.attachment"].search([
                ("res_model", "=", "stock.picking"),
                ("res_id", "=", self.id),
                ("mimetype", "=", "application/pdf"),
                (
                    "create_date",
                    ">=",
                    fields.Date.today(),
                ),
            ])

        ShippingLabel = self.env["shipping.label"]
        for attachment in attachments:
            # Copy attachment to shipment context
            new_att = attachment.copy({
                "res_model": "shipping.shipment",
                "res_id": shipment.id,
            })
            ShippingLabel.create({
                "shipment_id": shipment.id,
                "attachment_id": new_att.id,
                "label_type": "shipping",
            })

    def action_view_shipments(self):
        """Open shipments linked to this picking."""
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "shipping_management.action_shipping_shipment"
        )
        if self.shipment_count == 1:
            action["res_id"] = self.shipment_ids[0].id
            action["view_mode"] = "form"
            action["views"] = [(False, "form")]
        else:
            action["domain"] = [("picking_id", "=", self.id)]
        return action
