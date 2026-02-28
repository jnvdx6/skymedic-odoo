from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_sale_manager = fields.Boolean(
        compute='_compute_is_sale_manager',
    )
    custom_date_order = fields.Datetime(
        string="Fecha del pedido",
        help="Si se indica una fecha, se usará como fecha del pedido al confirmar "
             "en lugar de la fecha actual. Útil para introducir pedidos antiguos.",
    )
    skip_delivery_creation = fields.Boolean(
        string="No crear albarán",
        default=False,
        help="Si se marca, no se creará ningún albarán/entrega al confirmar el pedido.",
    )
    force_all_invoiced = fields.Boolean(
        string="Marcar como facturado",
        default=False,
        help="Si se marca, todas las líneas del pedido se considerarán ya facturadas. "
             "El pedido mostrará 'Totalmente facturado' en vez de 'Para facturar'.",
    )

    @api.depends_context('uid')
    def _compute_is_sale_manager(self):
        is_manager = self.env.user.has_group('sales_team.group_sale_manager')
        for order in self:
            order.is_sale_manager = is_manager

    def action_confirm(self):
        orders_with_custom_date = self.filtered('custom_date_order')
        saved_dates = {o.id: o.custom_date_order for o in orders_with_custom_date}
        result = super().action_confirm()
        for order in orders_with_custom_date:
            if order.id in saved_dates:
                order.date_order = saved_dates[order.id]
        return result

    def _action_confirm(self):
        skip_orders = self.filtered('skip_delivery_creation')
        normal_orders = self - skip_orders
        if normal_orders:
            super(SaleOrder, normal_orders)._action_confirm()
        if skip_orders:
            super(SaleOrder, skip_orders.with_context(skip_procurement=True))._action_confirm()

    def write(self, vals):
        result = super().write(vals)
        if 'force_all_invoiced' in vals:
            self.order_line.write({'force_invoiced': vals['force_all_invoiced']})
        return result
