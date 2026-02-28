from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    secondary_currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Secondary Invoice Currency',
        help='If set, invoices for this partner will show amounts '
             'converted to this currency alongside the main currency.',
    )
