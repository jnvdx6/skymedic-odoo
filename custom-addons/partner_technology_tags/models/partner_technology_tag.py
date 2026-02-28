from odoo import api, fields, models


class PartnerTechnologyTag(models.Model):
    _name = "partner.technology.tag"
    _description = "Tag de Tecnología del Cliente"
    _order = "tech_category, name"

    name = fields.Char(string="Tecnología", required=True)
    color = fields.Integer(string="Color")
    active = fields.Boolean(default=True)
    tech_category = fields.Selection(
        [
            ("dispositivo_skymedic", "Dispositivos Skymedic"),
            ("aparatologia", "Aparatología"),
            ("equipo_medico", "Equipos Médicos"),
            ("manipulo", "Manipulos"),
        ],
        string="Categoría",
    )
    tech_match_pattern = fields.Char(
        string="Patrón de búsqueda",
        help="Keywords separadas por coma para detectar esta tecnología en productos vendidos. Ej: fotoage,foto age",
    )
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
