import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ShippingBatchSendWizard(models.TransientModel):
    _name = "shipping.batch.send.wizard"
    _description = "Asistente de envío masivo"

    picking_ids = fields.Many2many(
        "stock.picking",
        string="Albaranes",
    )
    picking_count = fields.Integer(
        compute="_compute_picking_count",
        string="Nº albaranes",
    )
    error_log = fields.Text(
        string="Errores",
        readonly=True,
    )
    success_count = fields.Integer(
        string="Envíos exitosos",
        readonly=True,
    )
    state = fields.Selection(
        [("confirm", "Confirmar"), ("done", "Completado")],
        default="confirm",
    )

    @api.depends("picking_ids")
    def _compute_picking_count(self):
        for wizard in self:
            wizard.picking_count = len(wizard.picking_ids)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get("active_ids", [])
        if active_ids:
            pickings = self.env["stock.picking"].browse(active_ids)
            valid = pickings.filtered(
                lambda p: p.state == "done"
                and p.carrier_id
                and p.carrier_id.delivery_type
                not in ("fixed", "base_on_rule", False)
                and not p.carrier_tracking_ref
            )
            res["picking_ids"] = [(6, 0, valid.ids)]
        return res

    def action_send_all(self):
        """Send all selected pickings to their carrier."""
        self.ensure_one()
        if not self.picking_ids:
            raise UserError(_("No hay albaranes válidos para enviar."))

        errors = []
        success_count = 0
        for picking in self.picking_ids:
            try:
                picking.send_to_shipper()
                success_count += 1
                self.env.cr.commit()  # noqa: B034
            except Exception as e:
                _logger.exception(
                    "Batch send error for %s", picking.name,
                )
                errors.append(f"{picking.name}: {e}")
                self.env.cr.rollback()

        if errors:
            self.write({
                "state": "done",
                "error_log": "\n".join(errors),
                "success_count": success_count,
            })
            return {
                "type": "ir.actions.act_window",
                "res_model": self._name,
                "res_id": self.id,
                "view_mode": "form",
                "target": "new",
            }

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Envío masivo completado"),
                "message": _(
                    "%d albarán(es) enviado(s) correctamente."
                )
                % success_count,
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
