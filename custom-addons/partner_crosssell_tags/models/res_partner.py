import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# Keywords for the special "Cliente 360" tag (has_pattern == "__cliente_360__")
EQUIPMENT_KEYWORDS = [
    "fotoage", "bluelift", "dioxage", "radioage", "ledsmedical",
    "hr-3", "hr3", "etherea", "hegels", "sapphire", "dermajet",
    "ultrajet", "hidroage",
]
COSMETICS_KEYWORDS = [
    "colagenox", "hyalurox", "vitaox", "retinox", "fotoskinox",
    "skinox", "meso ox", "modelha", "exo ox", "dutaox",
    "cream", "crema", "serum",
]


class ResPartner(models.Model):
    _inherit = "res.partner"

    crosssell_tag_ids = fields.Many2many(
        "partner.crosssell.tag",
        string="Oportunidades Cross-sell",
    )

    def action_recompute_crosssell_tags(self):
        """Boton manual para recalcular tags de cross-sell."""
        self._update_crosssell_tags()

    def _get_confirmed_product_names(self):
        """Return lowercase product names from confirmed sale orders
        for this partner and its children."""
        self.ensure_one()
        partner_ids = (self | self.child_ids).ids
        orders = self.env["sale.order"].search([
            ("partner_id", "in", partner_ids),
            ("state", "in", ["sale", "done"]),
        ])
        if not orders:
            return set()
        lines = self.env["sale.order.line"].search([
            ("order_id", "in", orders.ids),
            ("product_id", "!=", False),
        ])
        product_names = set()
        for line in lines:
            name = (line.product_id.name or "").lower()
            if name:
                product_names.add(name)
            # Also include the display_name / sale description for broader matching
            desc = (line.name or "").lower()
            if desc:
                product_names.add(desc)
        return product_names

    @staticmethod
    def _keywords_match(product_names, pattern):
        """Check if ANY keyword from a comma-separated pattern matches
        any product name (substring match)."""
        if not pattern or not pattern.strip():
            return False
        keywords = [kw.strip().lower() for kw in pattern.split(",") if kw.strip()]
        combined_text = " ||| ".join(product_names)
        for kw in keywords:
            if kw in combined_text:
                return True
        return False

    def _update_crosssell_tags(self):
        """Assign cross-sell opportunity tags based on purchase history."""
        crosssell_tags = self.env["partner.crosssell.tag"].search(
            [], order="sequence, id"
        )
        if not crosssell_tags:
            return

        for partner in self:
            product_names = partner._get_confirmed_product_names()
            if not product_names:
                # No sales history — remove all crosssell tags
                if partner.crosssell_tag_ids:
                    partner.crosssell_tag_ids = [(5, 0, 0)]
                continue

            matched_tag_ids = []
            for tag in crosssell_tags:
                # Special logic for "Cliente 360"
                if tag.has_pattern == "__cliente_360__":
                    has_equipment = self._keywords_match(
                        product_names, ",".join(EQUIPMENT_KEYWORDS)
                    )
                    has_cosmetics = self._keywords_match(
                        product_names, ",".join(COSMETICS_KEYWORDS)
                    )
                    if has_equipment and has_cosmetics:
                        matched_tag_ids.append(tag.id)
                    continue

                # Normal pattern matching
                has_match = True
                missing_match = False

                # has_pattern: at least one keyword must appear
                if tag.has_pattern and tag.has_pattern.strip():
                    has_match = self._keywords_match(product_names, tag.has_pattern)
                else:
                    # No has_pattern means no positive requirement — skip tag
                    continue

                # missing_pattern: none of these keywords should appear
                if tag.missing_pattern and tag.missing_pattern.strip():
                    missing_match = self._keywords_match(
                        product_names, tag.missing_pattern
                    )

                if has_match and not missing_match:
                    matched_tag_ids.append(tag.id)

            # Only write if there is an actual change
            current_ids = sorted(partner.crosssell_tag_ids.ids)
            if current_ids != sorted(matched_tag_ids):
                partner.crosssell_tag_ids = [(6, 0, matched_tag_ids)]

    @api.model
    def _cron_update_crosssell_tags(self):
        """Cron: recalcular tags de cross-sell para partners con ventas."""
        partner_ids = (
            self.env["sale.order"]
            .search([("state", "in", ["sale", "done"])])
            .mapped("partner_id")
        )
        partners = partner_ids.filtered(lambda p: not p.parent_id)
        _logger.info(
            "Cron: actualizando tags de cross-sell para %d partners", len(partners)
        )
        batch_size = 50
        for i in range(0, len(partners), batch_size):
            batch = partners[i : i + batch_size]
            batch._update_crosssell_tags()
            self.env.cr.commit()
        _logger.info("Cron: tags de cross-sell actualizados correctamente")
