from . import models
from . import report

DUAL_CURRENCY_ARCH = '''<data>
    <!-- Setup secondary currency variables -->
    <xpath expr="//div[hasclass('article')]//div[hasclass('sky')]/t[@t-set='display_discount']"
           position="before">
        <t t-set="sec_data" t-value="secondary_currency_data.get(o.id, {}) if secondary_currency_data else {}"/>
        <t t-set="sec_currency" t-value="sec_data.get('secondary_currency')"/>
        <t t-set="has_sec" t-value="bool(sec_currency)"/>
    </xpath>

    <!-- Secondary amount on each product line -->
    <xpath expr="//table[hasclass('lt')]//tr[@t-if=&quot;line.display_type == 'product'&quot;]/td[last()]"
           position="inside">
        <t t-if="has_sec">
            <t t-set="line_sec" t-value="sec_data.get('line_amounts', {}).get(line.id, {})"/>
            <div style="font-size:6.5pt; color:#666; margin-top:1pt;">
                <span t-if="o.company_price_include == 'tax_excluded'"
                      t-out="line_sec.get('price_subtotal', 0)"
                      t-options='{"widget":"monetary","display_currency":sec_currency}'/>
                <span t-if="o.company_price_include == 'tax_included'"
                      t-out="line_sec.get('price_total', 0)"
                      t-options='{"widget":"monetary","display_currency":sec_currency}'/>
            </div>
        </t>
    </xpath>

    <!-- Secondary currency totals after main totals band -->
    <xpath expr="//div[hasclass('article')]//div[hasclass('sky')]/table[@style='width:100%; margin-top:10pt;']"
           position="after">
        <t t-if="has_sec">
            <div style="font-size:7pt; color:#888; text-align:right; margin-top:4pt; margin-bottom:2pt;">
                Tipo de cambio / Exchange rate
                (<span t-out="sec_data.get('rate_date')" t-options='{"widget":"date"}'/>):
                1 <span t-out="o.currency_id.name"/>
                = <span t-out="'%.4f' % sec_data.get('rate', 0)"/>
                <span t-out="sec_currency.name"/>
            </div>
            <table style="width:100%; margin-top:2pt;" cellspacing="0" cellpadding="0">
                <tr>
                    <td style="width:28%; vertical-align:top; padding-right:3pt;">
                        <table class="tt" style="width:100%;">
                            <tr><th style="background:#4a4a4a; color:#fff; font-size:6.5pt;">
                                Neto / Net (<span t-out="sec_currency.name"/>)
                            </th></tr>
                            <tr><td class="r b" style="font-size:10pt;">
                                <span t-out="sec_data.get('amount_untaxed', 0)"
                                      t-options='{"widget":"monetary","display_currency":sec_currency}'/>
                            </td></tr>
                        </table>
                    </td>
                    <td style="width:44%; vertical-align:top; padding:0 3pt;">
                        <table class="tt" style="width:100%;">
                            <tr><th class="r" style="background:#4a4a4a; color:#fff; font-size:6.5pt;">
                                Impuesto / Tax (<span t-out="sec_currency.name"/>)
                            </th></tr>
                            <tr><td class="r b" style="font-size:10pt;">
                                <span t-out="sec_data.get('amount_tax', 0)"
                                      t-options='{"widget":"monetary","display_currency":sec_currency}'/>
                            </td></tr>
                        </table>
                    </td>
                    <td style="width:28%; vertical-align:top; padding-left:3pt;">
                        <table class="tt" style="width:100%;">
                            <tr><th style="background:#4a4a4a; color:#fff;">
                                TOTAL (<span t-out="sec_currency.name"/>)
                            </th></tr>
                            <tr><td class="r" style="font-size:10pt; background:#4a4a4a; color:#fff; font-weight:bold; padding:5pt 8pt;">
                                <span t-out="sec_data.get('amount_total', 0)"
                                      t-options='{"widget":"monetary","display_currency":sec_currency}'/>
                            </td></tr>
                        </table>
                    </td>
                </tr>
            </table>
        </t>
    </xpath>

    <!-- Secondary amount on payment Due line -->
    <xpath expr="//tr[hasclass('b')]//td[@class='r']/span[@t-field='o.amount_residual']"
           position="after">
        <t t-if="has_sec">
            <div style="font-size:6.5pt; color:#666; margin-top:1pt;">
                <span t-out="sec_data.get('amount_residual', 0)"
                      t-options='{"widget":"monetary","display_currency":sec_currency}'/>
            </div>
        </t>
    </xpath>
</data>'''


def _post_init_hook(env):
    """Create the inheriting QWeb view and set default report for HANS BIOMED."""
    # --- 1. Create inheriting QWeb view for dual currency ---
    parent_view = env['ir.ui.view'].search([
        ('key', '=', 'account.report_invoice_document_copy_2'),
        ('type', '=', 'qweb'),
    ], limit=1)

    if parent_view:
        existing = env['ir.ui.view'].search([
            ('key', '=', 'invoice_dual_currency.report_invoice_document_dual_currency'),
        ], limit=1)
        if not existing:
            env['ir.ui.view'].create({
                'name': 'Dual Currency - Invoice Document',
                'type': 'qweb',
                'inherit_id': parent_view.id,
                'key': 'invoice_dual_currency.report_invoice_document_dual_currency',
                'arch_db': DUAL_CURRENCY_ARCH,
                'priority': 99,
                'mode': 'extension',
            })

    # --- 2. Set Skymedic report as default for HANS BIOMED journals ---
    skymedic_report = env['ir.actions.report'].search([
        ('report_name', '=', 'account.report_invoice_with_payments_copy_2'),
    ], limit=1)
    if skymedic_report:
        hans_biomed = env['res.company'].search([
            ('name', 'ilike', 'HANS BIOMED'),
        ], limit=1)
        if hans_biomed:
            journals = env['account.journal'].search([
                ('company_id', '=', hans_biomed.id),
                ('type', '=', 'sale'),
            ])
            if journals:
                journals.write({
                    'invoice_template_pdf_report_id': skymedic_report.id,
                })
