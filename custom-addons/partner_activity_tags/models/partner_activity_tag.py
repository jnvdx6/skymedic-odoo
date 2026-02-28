from odoo import api, fields, models


class PartnerActivityTag(models.Model):
    _name = "partner.activity.tag"
    _description = "Tag de Actividad de Compra"
    _order = "sequence, id"

    name = fields.Char(string="Periodo", required=True)
    color = fields.Integer(string="Color")
    sequence = fields.Integer(string="Secuencia", default=10)
    months_from = fields.Integer(
        string="Desde (meses)",
        help="Límite inferior en meses. 0 = hoy.",
    )
    months_to = fields.Integer(
        string="Hasta (meses)",
        help="Límite superior en meses. 0 = sin límite.",
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
