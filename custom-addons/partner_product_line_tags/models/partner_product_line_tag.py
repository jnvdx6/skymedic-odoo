from odoo import api, fields, models


class PartnerProductLineTag(models.Model):
    _name = "partner.product.line.tag"
    _description = "Tag de Línea de Producto"
    _order = "sequence, id"

    name = fields.Char(string="Línea de Producto", required=True)
    color = fields.Integer(string="Color")
    sequence = fields.Integer(string="Secuencia", default=10)
    product_match_pattern = fields.Char(
        string="Patrón de búsqueda",
        help="Keywords separadas por coma para detectar esta línea en productos vendidos",
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
