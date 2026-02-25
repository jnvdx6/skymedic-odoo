from odoo import _, fields, models
from odoo.exceptions import UserError


class ShippingBatchWizard(models.TransientModel):
    _name = "shipping.batch.wizard"
    _description = "Asistente de operaciones masivas de envíos"

    shipment_ids = fields.Many2many(
        "shipping.shipment",
        string="Envíos",
    )
    action_type = fields.Selection(
        [
            ("tracking", "Actualizar seguimiento"),
            ("labels", "Descargar etiquetas"),
        ],
        string="Acción",
        required=True,
        default="tracking",
    )

    def action_execute(self):
        """Execute the selected batch action."""
        self.ensure_one()
        if not self.shipment_ids:
            raise UserError(_("No se han seleccionado envíos."))

        if self.action_type == "tracking":
            return self._action_batch_tracking()
        elif self.action_type == "labels":
            return self._action_batch_labels()
        return {"type": "ir.actions.act_window_close"}

    def _action_batch_tracking(self):
        """Refresh tracking for all selected shipments."""
        self.shipment_ids.action_refresh_tracking()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Seguimiento actualizado"),
                "message": _(
                    "Se ha actualizado el seguimiento de %d envío(s)."
                )
                % len(self.shipment_ids),
                "type": "success",
                "sticky": False,
            },
        }

    def _action_batch_labels(self):
        """Download labels for all selected shipments."""
        labels = self.env["shipping.label"]
        for shipment in self.shipment_ids:
            if shipment.label_ids:
                labels |= shipment.label_ids.sorted(
                    "create_date", reverse=True
                )[0]

        if not labels:
            raise UserError(
                _(
                    "No hay etiquetas disponibles para los envíos "
                    "seleccionados."
                )
            )

        if len(labels) == 1:
            return labels[0].action_download()

        # Multiple labels: open labels list view
        return {
            "type": "ir.actions.act_window",
            "name": _("Etiquetas de envío"),
            "res_model": "shipping.label",
            "view_mode": "list,form",
            "domain": [("id", "in", labels.ids)],
            "target": "current",
        }
