from odoo import api, fields, models

# Priority map: lower = more urgent / actionable for display
_SHIPPING_STATE_PRIORITY = {
    "incident": 1,
    "in_transit": 2,
    "confirmed": 3,
    "draft": 4,
    "returned": 5,
    "delivered": 6,
    "cancelled": 7,
}


class SaleOrder(models.Model):
    _inherit = "sale.order"

    shipment_ids = fields.Many2many(
        "shipping.shipment",
        compute="_compute_shipment_ids",
        string="Envíos",
    )
    shipment_count = fields.Integer(
        compute="_compute_shipment_ids",
        string="Nº envíos",
    )
    shipping_state = fields.Selection(
        [
            ("no_shipping", "Sin envío"),
            ("draft", "Borrador"),
            ("confirmed", "Confirmado"),
            ("in_transit", "En tránsito"),
            ("incident", "Incidencia"),
            ("delivered", "Entregado"),
            ("cancelled", "Cancelado"),
            ("returned", "Devuelto"),
        ],
        string="Estado de envío",
        compute="_compute_shipping_state",
        store=True,
        readonly=True,
    )

    @api.depends("picking_ids.shipment_ids.state")
    def _compute_shipping_state(self):
        for order in self:
            shipments = order.picking_ids.shipment_ids
            if not shipments:
                order.shipping_state = "no_shipping"
                continue
            active = shipments.filtered(lambda s: s.state != "cancelled")
            if not active:
                order.shipping_state = "cancelled"
                continue
            order.shipping_state = min(
                active.mapped("state"),
                key=lambda s: _SHIPPING_STATE_PRIORITY.get(s, 99),
            )

    @api.depends("picking_ids.shipment_ids")
    def _compute_shipment_ids(self):
        for order in self:
            order.shipment_ids = order.picking_ids.shipment_ids
            order.shipment_count = len(order.shipment_ids)

    def action_view_shipments(self):
        """Open shipments linked to this sale order."""
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "shipping_management.action_shipping_shipment"
        )
        shipments = self.picking_ids.shipment_ids
        if len(shipments) == 1:
            action["res_id"] = shipments[0].id
            action["view_mode"] = "form"
            action["views"] = [(False, "form")]
        else:
            action["domain"] = [("id", "in", shipments.ids)]
        action["context"] = {}
        return action
