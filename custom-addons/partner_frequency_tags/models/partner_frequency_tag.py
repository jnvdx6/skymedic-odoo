from odoo import api, fields, models


class PartnerFrequencyTag(models.Model):
    _name = "partner.frequency.tag"
    _description = "Tag de Frecuencia de Compra"
    _order = "sequence, id"

    name = fields.Char(string="Frecuencia", required=True)
    color = fields.Integer(string="Color")
    sequence = fields.Integer(string="Secuencia", default=10)
    min_orders_per_year = fields.Integer(
        string="Pedidos mínimos/año",
        help="Número mínimo de pedidos confirmados en los últimos 12 meses.",
    )
    max_orders_per_year = fields.Integer(
        string="Pedidos máximos/año",
        help="Número máximo de pedidos confirmados en los últimos 12 meses. 0 = sin límite.",
    )
    active = fields.Boolean(default=True)
    partner_ids = fields.Many2many(
        "res.partner",
        string="Clientes",
    )
    partner_count = fields.Integer(
        string="Nº Clientes",
        compute="_compute_partner_count",
    )

    @api.depends("partner_ids")
    def _compute_partner_count(self):
        for tag in self:
            tag.partner_count = len(tag.partner_ids)
