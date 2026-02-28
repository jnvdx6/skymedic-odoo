from odoo import api, fields, models


class PartnerVolumeTag(models.Model):
    _name = "partner.volume.tag"
    _description = "Tag de Volumen de Compra"
    _order = "sequence, id"

    name = fields.Char(string="Nivel", required=True)
    color = fields.Integer(string="Color")
    sequence = fields.Integer(string="Secuencia", default=10)
    amount_from = fields.Float(
        string="Desde (\u20ac)",
        help="L\u00edmite inferior en euros.",
    )
    amount_to = fields.Float(
        string="Hasta (\u20ac)",
        help="L\u00edmite superior en euros. 0 = sin l\u00edmite.",
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
