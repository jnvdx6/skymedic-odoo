import logging

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    trend_tag_ids = fields.Many2many(
        "partner.trend.tag",
        string="Tendencia",
    )

    def action_recompute_trend_tags(self):
        """Bot\u00f3n manual para recalcular tag de tendencia."""
        self._update_trend_tags()

    def _update_trend_tags(self):
        """Asignar tag de tendencia seg\u00fan evoluci\u00f3n de pedidos confirmados."""
        trend_tags = self.env["partner.trend.tag"].search(
            [], order="sequence, id"
        )
        if not trend_tags:
            return

        # Index tags by trend_type for fast lookup
        tag_by_type = {}
        for tag in trend_tags:
            if tag.trend_type and tag.trend_type not in tag_by_type:
                tag_by_type[tag.trend_type] = tag

        today = fields.Date.context_today(self)
        six_months_ago = today - relativedelta(months=6)
        twelve_months_ago = today - relativedelta(months=12)

        SaleOrder = self.env["sale.order"]

        for partner in self:
            # Include child partner orders
            partner_ids = (partner | partner.child_ids).ids

            # Recent period: last 6 months
            recent_orders = SaleOrder.search([
                ("partner_id", "in", partner_ids),
                ("state", "in", ["sale", "done"]),
                ("date_order", ">=", six_months_ago),
            ])
            recent_amount = sum(recent_orders.mapped("amount_total"))

            # Previous period: 6-12 months ago
            previous_orders = SaleOrder.search([
                ("partner_id", "in", partner_ids),
                ("state", "in", ["sale", "done"]),
                ("date_order", ">=", twelve_months_ago),
                ("date_order", "<", six_months_ago),
            ])
            previous_amount = sum(previous_orders.mapped("amount_total"))

            # Check for any older orders (before 12 months)
            older_orders = SaleOrder.search([
                ("partner_id", "in", partner_ids),
                ("state", "in", ["sale", "done"]),
                ("date_order", "<", twelve_months_ago),
            ], limit=1)

            # Check first order date to determine if truly new
            first_order = SaleOrder.search([
                ("partner_id", "in", partner_ids),
                ("state", "in", ["sale", "done"]),
            ], order="date_order asc", limit=1)

            has_recent = recent_amount > 0
            has_previous = previous_amount > 0
            has_older = bool(older_orders)
            is_new_customer = (
                first_order
                and first_order.date_order.date() >= six_months_ago
            )

            # Classification logic
            trend_type = False

            if has_recent and not has_previous and is_new_customer:
                # New customer: has recent orders, no previous, first order within 6 months
                trend_type = "new"
            elif has_recent and has_previous:
                if recent_amount > previous_amount * 1.2:
                    # Growth: 20%+ increase
                    trend_type = "growth"
                elif recent_amount < previous_amount * 0.8:
                    # Decline: 20%+ decrease
                    trend_type = "decline"
                else:
                    # Stable: within 20% range
                    trend_type = "stable"
            elif has_recent and not has_previous and not is_new_customer:
                # Recovered: has recent orders, no previous, but has older history
                trend_type = "recovered"
            elif not has_recent and (has_previous or has_older):
                # Inactive: no recent orders but has historical orders
                trend_type = "inactive"

            if trend_type and trend_type in tag_by_type:
                matched_tag = tag_by_type[trend_type]
                current_ids = partner.trend_tag_ids.ids
                if current_ids != [matched_tag.id]:
                    partner.trend_tag_ids = [(6, 0, [matched_tag.id])]
            elif not trend_type:
                # No classification applicable — clear tags
                if partner.trend_tag_ids:
                    partner.trend_tag_ids = [(5, 0, 0)]

    @api.model
    def _cron_update_trend_tags(self):
        """Cron: recalcular tags de tendencia para partners con ventas."""
        partner_ids = (
            self.env["sale.order"]
            .search([("state", "in", ["sale", "done"])])
            .mapped("partner_id")
        )
        partners = partner_ids.filtered(lambda p: not p.parent_id)
        _logger.info(
            "Cron: actualizando tags de tendencia para %d partners", len(partners)
        )
        batch_size = 50
        for i in range(0, len(partners), batch_size):
            batch = partners[i : i + batch_size]
            batch._update_trend_tags()
            self.env.cr.commit()
        _logger.info("Cron: tags de tendencia actualizados correctamente")
