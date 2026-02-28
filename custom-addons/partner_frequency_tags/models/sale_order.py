from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        res = super().action_confirm()
        partners = self.mapped("partner_id").filtered(lambda p: not p.parent_id)
        child_partners = self.mapped("partner_id").filtered(lambda p: p.parent_id)
        partners |= child_partners.mapped("parent_id")
        if partners:
            partners._update_frequency_tags()
        return res
