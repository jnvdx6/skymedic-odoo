import logging

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression

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
        string="Nº envíos",
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
        domain = [
            ("res_model", "=", "stock.picking"),
            ("res_id", "=", self.id),
            ("mimetype", "=", "application/pdf"),
            ("name", "=like", "Label%"),
        ]
        attachments = self.env["ir.attachment"].search(domain)
        if not attachments and tracking:
            attachments = self.env["ir.attachment"].search([
                ("res_model", "=", "stock.picking"),
                ("res_id", "=", self.id),
                ("mimetype", "=", "application/pdf"),
                ("name", "ilike", tracking),
            ])

        ShippingLabel = self.env["shipping.label"]
        for attachment in attachments:
            new_att = attachment.copy({
                "res_model": "shipping.shipment",
                "res_id": shipment.id,
            })
            ShippingLabel.create({
                "shipment_id": shipment.id,
                "attachment_id": new_att.id,
                "label_type": "shipping",
            })

    def _link_return_labels_to_shipment(self, shipment, tracking_ref):
        """Find return label attachments and link to return shipment."""
        self.ensure_one()
        domain = [
            ("res_model", "=", "stock.picking"),
            ("res_id", "=", self.id),
            ("mimetype", "=", "application/pdf"),
            ("name", "ilike", "RETURN"),
        ]
        if tracking_ref:
            domain = expression.OR([
                domain,
                [
                    ("res_model", "=", "stock.picking"),
                    ("res_id", "=", self.id),
                    ("mimetype", "=", "application/pdf"),
                    ("name", "ilike", tracking_ref),
                ],
            ])
        attachments = self.env["ir.attachment"].search(domain)
        ShippingLabel = self.env["shipping.label"]
        for attachment in attachments:
            existing = ShippingLabel.search([
                ("shipment_id", "=", shipment.id),
                ("attachment_id", "=", attachment.id),
            ], limit=1)
            if existing:
                continue
            new_att = attachment.copy({
                "res_model": "shipping.shipment",
                "res_id": shipment.id,
            })
            ShippingLabel.create({
                "shipment_id": shipment.id,
                "attachment_id": new_att.id,
                "label_type": "return",
            })

    # ---- Label download from picking ----

    def action_download_shipping_label(self):
        """Download the latest shipping label from linked shipments."""
        self.ensure_one()
        shipments = self.shipment_ids.filtered(
            lambda s: s.label_ids and s.state != "cancelled"
        )
        if not shipments:
            raise UserError(
                _("No hay etiquetas de envío disponibles para este albarán.")
            )
        latest_label = self.env["shipping.label"]
        for shipment in shipments:
            labels = shipment.label_ids.filtered(
                lambda l: l.label_type == "shipping"
            )
            if labels:
                latest = labels.sorted("create_date", reverse=True)[0]
                if (
                    not latest_label
                    or latest.create_date > latest_label.create_date
                ):
                    latest_label = latest
        if not latest_label:
            # Fallback: any label type
            for shipment in shipments:
                if shipment.label_ids:
                    latest = shipment.label_ids.sorted(
                        "create_date", reverse=True,
                    )[0]
                    if (
                        not latest_label
                        or latest.create_date > latest_label.create_date
                    ):
                        latest_label = latest
        if not latest_label:
            raise UserError(
                _("No hay etiquetas de envío disponibles para este albarán.")
            )
        return latest_label.action_download()

    # ---- Carrier comparison ----

    def action_compare_carriers(self):
        """Open the carrier rate comparison wizard."""
        self.ensure_one()
        wizard = self.env["shipping.rate.compare.wizard"].create({
            "picking_id": self.id,
        })
        return wizard.action_compare_rates()

    # ---- Navigation ----

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
