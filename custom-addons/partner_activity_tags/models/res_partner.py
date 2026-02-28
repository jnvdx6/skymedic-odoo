import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    activity_tag_ids = fields.Many2many(
        "partner.activity.tag",
        string="Actividad de Compra",
    )
    last_sale_date = fields.Date(
        string="Última venta",
        compute="_compute_last_sale_date",
        store=True,
    )

    @api.depends("sale_order_ids.state", "sale_order_ids.date_order")
    def _compute_last_sale_date(self):
        for partner in self:
            orders = self.env["sale.order"].search(
                [
                    ("partner_id", "=", partner.id),
                    ("state", "in", ["sale", "done"]),
                ],
                order="date_order desc",
                limit=1,
            )
            partner.last_sale_date = orders.date_order.date() if orders else False

    def action_recompute_activity_tags(self):
        """Botón manual para recalcular tag de actividad."""
        self._update_activity_tags()

    def _update_activity_tags(self):
        """Asignar tag de actividad según la fecha de última compra."""
        activity_tags = self.env["partner.activity.tag"].search(
            [], order="sequence, id"
        )
        if not activity_tags:
            return

        today = fields.Date.context_today(self)

        for partner in self:
            # Buscar última venta (incluyendo hijos)
            partner_ids = (partner | partner.child_ids).ids
            last_order = self.env["sale.order"].search(
                [
                    ("partner_id", "in", partner_ids),
                    ("state", "in", ["sale", "done"]),
                ],
                order="date_order desc",
                limit=1,
            )

            if not last_order:
                continue

            last_date = last_order.date_order.date()
            months_diff = (today.year - last_date.year) * 12 + (
                today.month - last_date.month
            )

            matched_tag = self.env["partner.activity.tag"]
            for tag in activity_tags:
                if tag.months_to == 0:
                    # Tag sin límite superior (ej: "+24 meses")
                    if months_diff >= tag.months_from:
                        matched_tag = tag
                        break
                elif tag.months_from <= months_diff < tag.months_to:
                    matched_tag = tag
                    break

            if matched_tag:
                current_ids = partner.activity_tag_ids.ids
                if current_ids != [matched_tag.id]:
                    partner.activity_tag_ids = [(6, 0, [matched_tag.id])]

    @api.model
    def _cron_update_activity_tags(self):
        """Cron: recalcular tags de actividad para partners con ventas."""
        partner_ids = (
            self.env["sale.order"]
            .search([("state", "in", ["sale", "done"])])
            .mapped("partner_id")
        )
        partners = partner_ids.filtered(lambda p: not p.parent_id)
        _logger.info(
            "Cron: actualizando tags de actividad para %d partners", len(partners)
        )
        batch_size = 50
        for i in range(0, len(partners), batch_size):
            batch = partners[i : i + batch_size]
            batch._update_activity_tags()
            self.env.cr.commit()
        _logger.info("Cron: tags de actividad actualizados correctamente")
