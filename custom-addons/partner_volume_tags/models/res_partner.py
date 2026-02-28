import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    volume_tag_ids = fields.Many2many(
        "partner.volume.tag",
        string="Volumen de Compra",
    )
    total_sales_amount = fields.Float(
        string="Total Ventas",
        compute="_compute_total_sales_amount",
        store=True,
    )

    @api.depends("sale_order_ids.state", "sale_order_ids.amount_total")
    def _compute_total_sales_amount(self):
        for partner in self:
            orders = self.env["sale.order"].search(
                [
                    ("partner_id", "=", partner.id),
                    ("state", "in", ["sale", "done"]),
                ],
            )
            partner.total_sales_amount = sum(orders.mapped("amount_total"))

    def action_recompute_volume_tags(self):
        """Bot\u00f3n manual para recalcular tag de volumen."""
        self._update_volume_tags()

    def _update_volume_tags(self):
        """Asignar tag de volumen seg\u00fan el total de ventas confirmadas."""
        volume_tags = self.env["partner.volume.tag"].search(
            [], order="sequence, id"
        )
        if not volume_tags:
            return

        for partner in self:
            # Sumar ventas (incluyendo hijos)
            partner_ids = (partner | partner.child_ids).ids
            orders = self.env["sale.order"].search(
                [
                    ("partner_id", "in", partner_ids),
                    ("state", "in", ["sale", "done"]),
                ],
            )
            total_amount = sum(orders.mapped("amount_total"))

            if not orders:
                continue

            matched_tag = self.env["partner.volume.tag"]
            for tag in volume_tags:
                if tag.amount_to == 0:
                    # Tag sin l\u00edmite superior (ej: "+50K\u20ac")
                    if total_amount >= tag.amount_from:
                        matched_tag = tag
                        break
                elif tag.amount_from <= total_amount < tag.amount_to:
                    matched_tag = tag
                    break

            if matched_tag:
                current_ids = partner.volume_tag_ids.ids
                if current_ids != [matched_tag.id]:
                    partner.volume_tag_ids = [(6, 0, [matched_tag.id])]

    @api.model
    def _cron_update_volume_tags(self):
        """Cron: recalcular tags de volumen para partners con ventas."""
        partner_ids = (
            self.env["sale.order"]
            .search([("state", "in", ["sale", "done"])])
            .mapped("partner_id")
        )
        partners = partner_ids.filtered(lambda p: not p.parent_id)
        _logger.info(
            "Cron: actualizando tags de volumen para %d partners", len(partners)
        )
        batch_size = 50
        for i in range(0, len(partners), batch_size):
            batch = partners[i : i + batch_size]
            batch._update_volume_tags()
            self.env.cr.commit()
        _logger.info("Cron: tags de volumen actualizados correctamente")
