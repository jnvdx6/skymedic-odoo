{
    "name": "Tags de Frecuencia de Compra en Contactos",
    "summary": "Clasifica contactos según su frecuencia de compra",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "author": "Skymedic",
    "license": "LGPL-3",
    "depends": ["contacts", "sale"],
    "data": [
        "security/ir.model.access.csv",
        "data/frequency_tags_data.xml",
        "data/frequency_cron.xml",
        "views/partner_frequency_tag_views.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "application": False,
}
