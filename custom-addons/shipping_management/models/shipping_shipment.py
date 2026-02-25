import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

SHIPMENT_STATES = [
    ("draft", "Borrador"),
    ("confirmed", "Confirmado"),
    ("in_transit", "En tránsito"),
    ("delivered", "Entregado"),
    ("cancelled", "Cancelado"),
    ("returned", "Devuelto"),
]


class ShippingShipment(models.Model):
    _name = "shipping.shipment"
    _description = "Envío"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"
    _rec_name = "name"

    # ---- Core fields ----

    name = fields.Char(
        string="Referencia",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    state = fields.Selection(
        SHIPMENT_STATES,
        string="Estado",
        default="draft",
        tracking=True,
        required=True,
        copy=False,
    )

    # ---- Relations ----

    picking_id = fields.Many2one(
        "stock.picking",
        string="Orden de entrega",
        ondelete="cascade",
        index=True,
        copy=False,
    )
    carrier_id = fields.Many2one(
        "delivery.carrier",
        string="Transportista",
        required=True,
        index=True,
    )
    carrier_type = fields.Selection(
        related="carrier_id.delivery_type",
        string="Tipo de transportista",
        store=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Destinatario",
        related="picking_id.partner_id",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        related="picking_id.company_id",
        store=True,
        readonly=True,
    )

    # ---- Tracking ----

    tracking_ref = fields.Char(
        string="Número de seguimiento",
        copy=False,
        tracking=True,
        index=True,
    )
    tracking_url = fields.Char(
        string="URL de seguimiento",
        compute="_compute_tracking_url",
    )
    expedition_code = fields.Char(
        string="Código de expedición",
        copy=False,
        help="Código interno del transportista para esta expedición",
    )
    last_tracking_update = fields.Datetime(
        string="Última actualización",
        copy=False,
        readonly=True,
    )
    tracking_status_raw = fields.Text(
        string="Estado de seguimiento (detalle)",
        copy=False,
        readonly=True,
    )

    # ---- Shipping details ----

    origin = fields.Char(
        string="Origen",
        related="picking_id.origin",
        store=True,
        readonly=True,
    )
    shipping_weight = fields.Float(
        string="Peso",
        related="picking_id.shipping_weight",
        readonly=True,
    )
    number_of_packages = fields.Integer(
        string="Bultos",
    )
    shipping_cost = fields.Float(
        string="Coste de envío",
    )

    # ---- Dates ----

    ship_date = fields.Datetime(
        string="Fecha de envío",
        copy=False,
    )
    delivery_date = fields.Datetime(
        string="Fecha de entrega",
        copy=False,
    )

    # ---- Labels ----

    label_ids = fields.One2many(
        "shipping.label",
        "shipment_id",
        string="Etiquetas",
    )
    label_count = fields.Integer(
        compute="_compute_label_count",
        string="Etiquetas",
    )

    # ---- Computed ----

    @api.depends("carrier_id", "tracking_ref", "picking_id")
    def _compute_tracking_url(self):
        for shipment in self:
            if (
                shipment.carrier_id
                and shipment.tracking_ref
                and shipment.picking_id
            ):
                shipment.tracking_url = shipment.carrier_id.get_tracking_link(
                    shipment.picking_id
                )
            else:
                shipment.tracking_url = False

    def _compute_label_count(self):
        for shipment in self:
            shipment.label_count = len(shipment.label_ids)

    # ---- CRUD ----

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("shipping.shipment")
                    or _("New")
                )
        return super().create(vals_list)

    # ---- State transitions ----

    def action_confirm(self):
        self.filtered(lambda s: s.state == "draft").write({
            "state": "confirmed",
            "ship_date": fields.Datetime.now(),
        })

    def action_cancel(self):
        for shipment in self.filtered(
            lambda s: s.state in ("draft", "confirmed")
        ):
            if shipment.picking_id and shipment.tracking_ref:
                try:
                    shipment.picking_id.cancel_shipment()
                except UserError as e:
                    _logger.warning(
                        "Error cancelling shipment %s: %s",
                        shipment.name,
                        e,
                    )
            shipment.write({"state": "cancelled"})

    def action_mark_in_transit(self):
        self.filtered(lambda s: s.state == "confirmed").write({
            "state": "in_transit",
        })

    def action_mark_delivered(self):
        self.filtered(
            lambda s: s.state in ("confirmed", "in_transit")
        ).write({
            "state": "delivered",
            "delivery_date": fields.Datetime.now(),
        })

    def action_mark_returned(self):
        self.filtered(
            lambda s: s.state in ("in_transit", "delivered")
        ).write({
            "state": "returned",
        })

    def action_reset_to_draft(self):
        self.filtered(lambda s: s.state == "cancelled").write({
            "state": "draft",
        })

    # ---- Tracking ----

    def action_refresh_tracking(self):
        """Refresh tracking status from the carrier API."""
        for shipment in self:
            if not shipment.tracking_ref or not shipment.carrier_id:
                continue
            shipment.carrier_id._update_shipment_status(shipment)
            shipment.last_tracking_update = fields.Datetime.now()

    # ---- Labels ----

    def action_download_label(self):
        """Download the most recent label."""
        self.ensure_one()
        if not self.label_ids:
            raise UserError(
                _("No hay etiquetas disponibles para este envío.")
            )
        latest = self.label_ids.sorted("create_date", reverse=True)[0]
        return latest.action_download()

    def action_view_labels(self):
        """Open labels linked to this shipment."""
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "shipping_management.action_shipping_label"
        )
        action["domain"] = [("shipment_id", "=", self.id)]
        return action

    def action_reprint_label(self):
        """Re-fetch the label from the carrier API."""
        for shipment in self:
            shipment.carrier_id._reprint_shipment_label(shipment)

    # ---- Cron ----

    @api.model
    def _cron_update_tracking_status(self):
        """Scheduled action: update tracking for active shipments."""
        shipments = self.search([
            ("state", "in", ("confirmed", "in_transit")),
            ("tracking_ref", "!=", False),
            ("carrier_id", "!=", False),
        ])
        _logger.info(
            "Shipping cron: updating tracking for %d shipments",
            len(shipments),
        )
        for shipment in shipments:
            try:
                shipment.action_refresh_tracking()
                self.env.cr.commit()  # noqa: B034
            except Exception:
                _logger.exception(
                    "Error updating tracking for shipment %s",
                    shipment.name,
                )
                self.env.cr.rollback()
        _logger.info("Shipping cron: tracking update complete")
