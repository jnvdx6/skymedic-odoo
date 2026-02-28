from odoo import api, fields, models


class PartnerCrosssellTag(models.Model):
    _name = "partner.crosssell.tag"
    _description = "Tag de Oportunidad Cross-sell"
    _order = "sequence, id"

    name = fields.Char(string="Nombre", required=True)
    color = fields.Integer(string="Color")
    sequence = fields.Integer(string="Secuencia", default=10)
    has_pattern = fields.Char(
        string="Patrón requerido",
        help="Keywords que el cliente DEBE tener en sus compras (separados por coma)",
    )
    missing_pattern = fields.Char(
        string="Patrón ausente",
        help="Keywords que el cliente NO debe tener en sus compras (separados por coma)",
    )
    active = fields.Boolean(default=True)
    partner_ids = fields.Many2many(
        "res.partner",
        string="Clientes",
    )
    partner_count = fields.Integer(
        string="N Clientes",
        compute="_compute_partner_count",
    )

    @api.depends("partner_ids")
    def _compute_partner_count(self):
        for tag in self:
            tag.partner_count = len(tag.partner_ids)
