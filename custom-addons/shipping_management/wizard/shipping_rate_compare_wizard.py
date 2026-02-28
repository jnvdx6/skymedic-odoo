import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ShippingRateCompareWizard(models.TransientModel):
    _name = "shipping.rate.compare.wizard"
    _description = "Comparar tarifas de transportistas"

    picking_id = fields.Many2one(
        "stock.picking",
        string="Albarán",
        required=True,
    )
    line_ids = fields.One2many(
        "shipping.rate.compare.line",
        "wizard_id",
        string="Tarifas",
    )

    def action_compare_rates(self):
        """Compare rates from all active carriers for this picking."""
        self.ensure_one()
        self.line_ids.unlink()

        sale = self.picking_id.sale_id
        if not sale:
            raise UserError(
                _(
                    "Este albarán no tiene pedido de venta vinculado. "
                    "La comparación de tarifas requiere un pedido de venta."
                )
            )

        carriers = self.env["delivery.carrier"].search([
            ("active", "=", True),
            ("delivery_type", "not in", ("fixed", "base_on_rule")),
        ])
        if not carriers:
            raise UserError(
                _("No hay transportistas activos con integración API.")
            )

        lines = []
        for carrier in carriers:
            try:
                result = carrier.rate_shipment(sale)
                if result.get("success"):
                    lines.append((0, 0, {
                        "carrier_id": carrier.id,
                        "price": result.get("price", 0),
                        "delivery_days": carrier.sla_delivery_days,
                        "warning": result.get("warning_message") or "",
                    }))
                else:
                    lines.append((0, 0, {
                        "carrier_id": carrier.id,
                        "price": 0,
                        "error": result.get("error_message")
                        or _("Error desconocido"),
                    }))
            except Exception as e:
                _logger.warning(
                    "Rate comparison error for carrier %s: %s",
                    carrier.name, e,
                )
                lines.append((0, 0, {
                    "carrier_id": carrier.id,
                    "price": 0,
                    "error": str(e)[:200],
                }))

        self.write({"line_ids": lines})
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_select_carrier(self):
        """Assign the selected carrier to the picking."""
        self.ensure_one()
        selected = self.line_ids.filtered("is_selected")
        if not selected:
            raise UserError(_("Seleccione un transportista."))
        if len(selected) > 1:
            raise UserError(_("Seleccione solo un transportista."))
        self.picking_id.carrier_id = selected[0].carrier_id
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Transportista asignado"),
                "message": _(
                    "Se ha asignado %s al albarán %s."
                )
                % (selected[0].carrier_id.name, self.picking_id.name),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }


class ShippingRateCompareLine(models.TransientModel):
    _name = "shipping.rate.compare.line"
    _description = "Línea de comparación de tarifas"
    _order = "error asc, price asc"

    wizard_id = fields.Many2one(
        "shipping.rate.compare.wizard",
        required=True,
        ondelete="cascade",
    )
    carrier_id = fields.Many2one(
        "delivery.carrier",
        string="Transportista",
        readonly=True,
    )
    carrier_type = fields.Selection(
        related="carrier_id.delivery_type",
        string="Tipo",
        readonly=True,
    )
    price = fields.Float(
        string="Precio estimado (€)",
        readonly=True,
    )
    delivery_days = fields.Integer(
        string="Plazo SLA (días)",
        readonly=True,
    )
    warning = fields.Char(
        string="Aviso",
        readonly=True,
    )
    error = fields.Char(
        string="Error",
        readonly=True,
    )
    is_selected = fields.Boolean(
        string="Sel.",
    )
