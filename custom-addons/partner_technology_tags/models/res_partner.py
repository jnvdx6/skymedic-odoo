import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    technology_tag_ids = fields.Many2many(
        "partner.technology.tag",
        string="Tecnologías",
    )

    def action_recompute_technology_tags(self):
        """Botón manual para recalcular tags de tecnología."""
        self._update_technology_tags()

    def _update_technology_tags(self):
        """Escanear ventas confirmadas y asignar tags de tecnología."""
        tech_tags = self.env["partner.technology.tag"].search(
            [("tech_match_pattern", "!=", False)]
        )
        if not tech_tags:
            return

        for partner in self:
            partner_ids = (partner | partner.child_ids).ids
            sale_lines = self.env["sale.order.line"].search(
                [
                    ("order_id.partner_id", "in", partner_ids),
                    ("order_id.state", "in", ["sale", "done"]),
                ]
            )

            product_names = set()
            for line in sale_lines:
                tmpl = line.product_id.product_tmpl_id
                if not tmpl:
                    continue
                name = tmpl.name
                if name:
                    product_names.add(str(name).lower())

            if not product_names:
                continue

            all_text = " ||| ".join(product_names)
            matched_ids = []
            for tag in tech_tags:
                patterns = [
                    p.strip().lower()
                    for p in tag.tech_match_pattern.split(",")
                    if p.strip()
                ]
                if any(pattern in all_text for pattern in patterns):
                    matched_ids.append(tag.id)

            if matched_ids != partner.technology_tag_ids.ids:
                partner.technology_tag_ids = [(6, 0, matched_ids)]

    @api.model
    def _cron_update_technology_tags(self):
        """Cron: recalcular tags de tecnología para partners con ventas."""
        partner_ids = (
            self.env["sale.order"]
            .search([("state", "in", ["sale", "done"])])
            .mapped("partner_id")
        )
        partners = partner_ids.filtered(lambda p: not p.parent_id)
        _logger.info(
            "Cron: actualizando tags de tecnología para %d partners", len(partners)
        )
        batch_size = 50
        for i in range(0, len(partners), batch_size):
            batch = partners[i : i + batch_size]
            batch._update_technology_tags()
            self.env.cr.commit()
        _logger.info("Cron: tags de tecnología actualizados correctamente")
