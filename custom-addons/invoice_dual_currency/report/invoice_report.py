from odoo import api, models


class ReportInvoiceWithPaymentsCopy2(models.AbstractModel):
    _name = 'report.account.report_invoice_with_payments_copy_2'
    _description = 'Skymedic Invoice Report with Dual Currency'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.move'].browse(docids)

        secondary_currency_data = {}
        for invoice in docs:
            sec_data = invoice._get_secondary_currency_data()
            if sec_data:
                secondary_currency_data[invoice.id] = sec_data

        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': docs,
            'report_type': data.get('report_type') if data else '',
            'secondary_currency_data': secondary_currency_data,
        }
