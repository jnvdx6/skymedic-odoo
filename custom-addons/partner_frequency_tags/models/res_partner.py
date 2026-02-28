import logging
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    frequency_tag_ids = fields.Many2many(
        "partner.frequency.tag",
        string="Frecuencia de Compra",
    )

    def action_recompute_frequency_tags(self):
        """Botón manual para recalcular tag de frecuencia."""
        self._update_frequency_tags()

    def _update_frequency_tags(self):
        """Asignar tag de frecuencia según el número de pedidos en los últimos 12 meses."""
        frequency_tags = self.env["partner.frequency.tag"].search(
            [], order="sequence, id"
        )
        if not frequency_tags:
            return

        today = fields.Date.context_today(self)
        date_from = today - relativedelta(years=1)

        for partner in self:
            # Contar pedidos confirmados (incluyendo hijos)
            partner_ids = (partner | partner.child_ids).ids
            order_count = self.env["sale.order"].search_count(
                [
                    ("partner_id", "in", partner_ids),
                    ("state", "in", ["sale", "done"]),
                    ("date_order", ">=", fields.Datetime.to_datetime(date_from)),
                ],
            )

            matched_tag = self.env["partner.frequency.tag"]
            for tag in frequency_tags:
                if tag.max_orders_per_year == 0:
                    # Tag sin límite superior (ej: "12+/año")
                    if order_count >= tag.min_orders_per_year:
                        matched_tag = tag
                        break
                elif tag.min_orders_per_year <= order_count < tag.max_orders_per_year:
                    matched_tag = tag
                    break

            if matched_tag:
                current_ids = partner.frequency_tag_ids.ids
                if current_ids != [matched_tag.id]:
                    partner.frequency_tag_ids = [(6, 0, [matched_tag.id])]

    @api.model
    def _cron_update_frequency_tags(self):
        """Cron: recalcular tags de frecuencia para partners con ventas."""
        partner_ids = (
            self.env["sale.order"]
            .search([("state", "in", ["sale", "done"])])
            .mapped("partner_id")
        )
        partners = partner_ids.filtered(lambda p: not p.parent_id)
        _logger.info(
            "Cron: actualizando tags de frecuencia para %d partners", len(partners)
        )
        batch_size = 50
        for i in range(0, len(partners), batch_size):
            batch = partners[i : i + batch_size]
            batch._update_frequency_tags()
            self.env.cr.commit()
        _logger.info("Cron: tags de frecuencia actualizados correctamente")
