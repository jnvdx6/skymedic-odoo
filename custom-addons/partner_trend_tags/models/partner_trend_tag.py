from odoo import api, fields, models


class PartnerTrendTag(models.Model):
    _name = "partner.trend.tag"
    _description = "Tag de Tendencia de Compra"
    _order = "sequence, id"

    name = fields.Char(string="Tendencia", required=True)
    color = fields.Integer(string="Color")
    sequence = fields.Integer(string="Secuencia", default=10)
    trend_type = fields.Selection(
        [
            ("growth", "Crecimiento"),
            ("stable", "Estable"),
            ("decline", "Declive"),
            ("recovered", "Recuperado"),
            ("new", "Nuevo"),
            ("inactive", "Inactivo"),
        ],
        string="Tipo de Tendencia",
    )
    active = fields.Boolean(default=True)
    partner_ids = fields.Many2many(
        "res.partner",
        string="Clientes",
    )
    partner_count = fields.Integer(
        string="N\u00ba Clientes",
        compute="_compute_partner_count",
    )

    @api.depends("partner_ids")
    def _compute_partner_count(self):
        for tag in self:
            tag.partner_count = len(tag.partner_ids)
