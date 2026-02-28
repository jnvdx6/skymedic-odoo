{
    "name": "Tags de Tendencia de Compra en Contactos",
    "summary": "Clasifica contactos según la tendencia de su facturación",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "author": "Skymedic",
    "license": "LGPL-3",
    "depends": ["contacts", "sale"],
    "data": [
        "security/ir.model.access.csv",
        "data/trend_tags_data.xml",
        "data/trend_cron.xml",
        "views/partner_trend_tag_views.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "application": False,
}
