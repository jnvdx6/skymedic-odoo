{
    "name": "Invoice Dual Currency",
    "summary": "Show secondary currency on Skymedic invoice reports",
    "version": "19.0.1.0.0",
    "category": "Accounting",
    "author": "Skymedic",
    "license": "AGPL-3",
    "depends": [
        "account",
    ],
    "data": [
        "views/res_partner_views.xml",
    ],
    "post_init_hook": "_post_init_hook",
    "installable": True,
    "application": False,
}
