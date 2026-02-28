from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_secondary_currency_data(self):
        """Return secondary currency conversion data for the invoice report.

        Returns an empty dict when no secondary currency applies.
        """
        self.ensure_one()
        partner = self.commercial_partner_id
        sec_currency = partner.secondary_currency_id

        if not sec_currency or sec_currency == self.currency_id:
            return {}

        inv_currency = self.currency_id
        company = self.company_id
        date = self.invoice_date or fields.Date.context_today(self)

        rate = inv_currency._get_conversion_rate(
            inv_currency, sec_currency, company, date,
        )

        def convert(amount):
            return sec_currency.round(amount * rate)

        # Line amounts
        line_amounts = {}
        for line in self._get_move_lines_to_report():
            if line.display_type == 'product':
                line_amounts[line.id] = {
                    'price_subtotal': convert(line.price_subtotal),
                    'price_total': convert(line.price_total),
                    'price_unit': convert(line.price_unit),
                }

        # Payment amounts
        payment_amounts = {}
        payments_widget = self.sudo().invoice_payments_widget
        if payments_widget and payments_widget.get('content'):
            for idx, pv in enumerate(payments_widget['content']):
                if pv.get('is_exchange', 0) == 0:
                    payment_amounts[idx] = convert(pv['amount'])

        # Due line amounts
        due_amounts = {}
        due_lines = self.line_ids.filtered(
            lambda l: l.account_id.account_type == 'asset_receivable'
        ).sorted('date_maturity')
        for dl in due_lines:
            due_amounts[dl.id] = convert(dl.debit)

        return {
            'secondary_currency': sec_currency,
            'rate': rate,
            'rate_date': date,
            'amount_untaxed': convert(self.amount_untaxed),
            'amount_tax': convert(self.amount_tax),
            'amount_total': convert(self.amount_total),
            'amount_residual': convert(self.amount_residual),
            'line_amounts': line_amounts,
            'payment_amounts': payment_amounts,
            'due_amounts': due_amounts,
        }
