{
    "name": "Tags de Volumen de Compra en Contactos",
    "summary": "Clasifica contactos por volumen total de facturación",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "author": "Skymedic",
    "license": "LGPL-3",
    "depends": ["contacts", "sale"],
    "data": [
        "security/ir.model.access.csv",
        "data/volume_tags_data.xml",
        "data/volume_cron.xml",
        "views/partner_volume_tag_views.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "application": False,
}
