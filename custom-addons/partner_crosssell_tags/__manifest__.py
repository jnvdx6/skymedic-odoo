{
    "name": "Tags de Oportunidad Cross-sell en Contactos",
    "summary": "Identifica oportunidades de venta cruzada según el historial de compras",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "author": "Skymedic",
    "license": "LGPL-3",
    "depends": ["contacts", "sale"],
    "data": [
        "security/ir.model.access.csv",
        "data/crosssell_tags_data.xml",
        "data/crosssell_cron.xml",
        "views/partner_crosssell_tag_views.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "application": False,
}
