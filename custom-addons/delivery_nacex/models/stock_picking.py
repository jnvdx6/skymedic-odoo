# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from markupsafe import Markup

from odoo import fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    nacex_with_return = fields.Boolean(
        string="Con devolución",
        related="carrier_id.nacex_with_return",
        readonly=False,
        help="Activar envío con devolución para entregas NACEX",
    )
    nacex_expedition_code = fields.Char(
        string="Código de expedición NACEX",
        copy=False,
        readonly=True,
        help="Código interno de expedición NACEX (codExp), "
        "utilizado para cancelación y obtención de etiquetas",
    )
    nacex_tracking_status = fields.Text(
        string="Estado de seguimiento NACEX",
        copy=False,
        readonly=True,
    )
    nacex_tracking_status_date = fields.Datetime(
        string="Última comprobación de estado",
        copy=False,
        readonly=True,
    )

    def action_nacex_check_status(self):
        """Check NACEX tracking status for this picking."""
        self.ensure_one()
        if not self.carrier_tracking_ref:
            raise UserError(
                self.env._(
                    "No hay referencia de seguimiento disponible "
                    "para consultar el estado."
                )
            )
        self.carrier_id._nacex_get_info_envio(self)

    def action_nacex_schedule_pickup(self):
        """Open the NACEX pickup scheduling wizard."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Programar recogida NACEX"),
            "res_model": "nacex.pickup.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_picking_id": self.id},
        }

    def action_nacex_return_label(self):
        """Generate a return label for this NACEX shipment."""
        self.ensure_one()
        if not self.carrier_tracking_ref:
            raise UserError(
                self.env._(
                    "No hay referencia de seguimiento. "
                    "Primero envíe el albarán al transportista."
                )
            )
        self.carrier_id.nacex_get_return_label(self)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": self.env._("Etiqueta de devolución"),
                "message": self.env._(
                    "Se ha generado la etiqueta de devolución NACEX. "
                    "Puede descargarla desde los adjuntos."
                ),
                "type": "success",
                "sticky": False,
            },
        }
