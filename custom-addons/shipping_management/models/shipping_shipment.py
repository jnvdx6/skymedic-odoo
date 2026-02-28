import logging
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

SHIPMENT_STATES = [
    ("draft", "Borrador"),
    ("confirmed", "Confirmado"),
    ("in_transit", "En tránsito"),
    ("incident", "Incidencia"),
    ("delivered", "Entregado"),
    ("cancelled", "Cancelado"),
    ("returned", "Devuelto"),
]

SLA_STATUS = [
    ("on_time", "En plazo"),
    ("warning", "Próximo a vencer"),
    ("overdue", "Fuera de plazo"),
    ("na", "N/A"),
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

    # ---- SLA ----

    sla_deadline = fields.Date(
        string="Fecha límite SLA",
        compute="_compute_sla_deadline",
        store=True,
    )
    sla_status = fields.Selection(
        SLA_STATUS,
        string="Estado SLA",
        compute="_compute_sla_status",
        store=True,
    )

    # ---- Return ----

    return_shipment_id = fields.Many2one(
        "shipping.shipment",
        string="Envío de devolución",
        copy=False,
    )
    original_shipment_id = fields.Many2one(
        "shipping.shipment",
        string="Envío original",
        copy=False,
    )
    is_return = fields.Boolean(
        string="Es devolución",
        default=False,
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
        string="Nº etiquetas",
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

    @api.depends("ship_date", "carrier_id.sla_delivery_days")
    def _compute_sla_deadline(self):
        for shipment in self:
            if shipment.ship_date and shipment.carrier_id.sla_delivery_days:
                ship_date = shipment.ship_date.date()
                shipment.sla_deadline = ship_date + timedelta(
                    days=shipment.carrier_id.sla_delivery_days,
                )
            else:
                shipment.sla_deadline = False

    @api.depends("sla_deadline", "state", "delivery_date")
    def _compute_sla_status(self):
        today = fields.Date.context_today(self)
        for shipment in self:
            if shipment.state in ("cancelled", "draft"):
                shipment.sla_status = "na"
            elif shipment.state == "delivered":
                if (
                    shipment.delivery_date
                    and shipment.sla_deadline
                ):
                    delivered_date = shipment.delivery_date.date()
                    shipment.sla_status = (
                        "on_time"
                        if delivered_date <= shipment.sla_deadline
                        else "overdue"
                    )
                else:
                    shipment.sla_status = "na"
            elif shipment.state == "returned":
                shipment.sla_status = "overdue"
            elif not shipment.sla_deadline:
                shipment.sla_status = "na"
            elif today > shipment.sla_deadline:
                shipment.sla_status = "overdue"
            elif today >= shipment.sla_deadline - timedelta(days=1):
                shipment.sla_status = "warning"
            else:
                shipment.sla_status = "on_time"

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

    # ---- Returns ----

    def action_generate_return(self):
        """Generate a return shipment from the carrier API."""
        self.ensure_one()
        if self.state not in ("in_transit", "delivered", "incident"):
            raise UserError(
                _(
                    "Solo se pueden generar devoluciones para envíos "
                    "en tránsito, entregados o con incidencia."
                )
            )
        if self.return_shipment_id:
            raise UserError(
                _("Ya existe un envío de devolución: %s")
                % self.return_shipment_id.name
            )

        result = self.carrier_id._generate_return_shipment(self)

        return_vals = {
            "picking_id": self.picking_id.id if self.picking_id else False,
            "carrier_id": self.carrier_id.id,
            "tracking_ref": result.get("tracking_ref"),
            "expedition_code": result.get("expedition_code", False),
            "state": "confirmed",
            "ship_date": fields.Datetime.now(),
            "is_return": True,
            "original_shipment_id": self.id,
        }
        return_shipment = self.create(return_vals)

        if self.picking_id:
            self.picking_id._link_return_labels_to_shipment(
                return_shipment, result.get("tracking_ref"),
            )

        self.return_shipment_id = return_shipment.id
        self.message_post(
            body=_(
                "Envío de devolución creado: <a href='#' "
                "data-oe-model='shipping.shipment' data-oe-id='%d'>%s</a>"
            )
            % (return_shipment.id, return_shipment.name),
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "shipping.shipment",
            "res_id": return_shipment.id,
            "view_mode": "form",
            "target": "current",
        }

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

    @api.model
    def _cron_check_sla_alerts(self):
        """Scheduled action: create activities for shipments exceeding SLA."""
        today = fields.Date.context_today(self)
        overdue_shipments = self.search([
            ("state", "in", ("confirmed", "in_transit", "incident")),
            ("sla_deadline", "!=", False),
            ("sla_deadline", "<", today),
        ])
        _logger.info(
            "SLA cron: found %d overdue shipments", len(overdue_shipments),
        )
        activity_type = self.env.ref(
            "mail.mail_activity_data_todo", raise_if_not_found=False,
        )
        if not activity_type:
            _logger.warning("SLA cron: mail_activity_data_todo not found")
            return

        for shipment in overdue_shipments:
            existing = self.env["mail.activity"].search([
                ("res_model", "=", "shipping.shipment"),
                ("res_id", "=", shipment.id),
                ("activity_type_id", "=", activity_type.id),
                ("summary", "ilike", "SLA"),
            ], limit=1)
            if existing:
                continue

            user_id = False
            if shipment.picking_id and shipment.picking_id.sale_id:
                user_id = shipment.picking_id.sale_id.user_id.id
            if not user_id:
                user_id = self.env.uid

            days_overdue = (today - shipment.sla_deadline).days
            shipment.activity_schedule(
                act_type_xmlid="mail.mail_activity_data_todo",
                summary=_("SLA superado (%d día(s) de retraso)") % days_overdue,
                note=_(
                    "El envío %s lleva %d día(s) sin entregarse. "
                    "Plazo SLA: %s. Transportista: %s."
                )
                % (
                    shipment.name,
                    days_overdue,
                    shipment.sla_deadline,
                    shipment.carrier_id.name,
                ),
                date_deadline=today,
                user_id=user_id,
            )
        _logger.info("SLA cron: alert check complete")
