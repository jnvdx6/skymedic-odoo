from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    force_invoiced = fields.Boolean(
        string="Forzar facturado",
        default=False,
        help="Marca esta línea como ya facturada.",
    )

    @api.depends('force_invoiced')
    def _compute_invoice_status(self):
        super()._compute_invoice_status()
        for line in self:
            if line.force_invoiced and line.state == 'sale':
                line.invoice_status = 'invoiced'
