{
    "name": "Delivery NACEX",
    "summary": "Integración de operaciones de envío NACEX desde Odoo",
    "version": "19.0.3.0.0",
    "category": "Inventory/Delivery",
    "author": "Open Source Integrators, Odoo Community Association (OCA)",
    "maintainer": "Open Source Integrators",
    "website": "https://github.com/OCA/delivery-carrier",
    "license": "AGPL-3",
    "depends": [
        "delivery_carrier_account",
        "delivery_carrier_agency",
        "delivery_package_number",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/nacex_email_template.xml",
        "wizard/nacex_pickup_wizard.xml",
        "views/delivery_carrier.xml",
        "views/stock_picking.xml",
    ],
    "installable": True,
    "application": False,
}
