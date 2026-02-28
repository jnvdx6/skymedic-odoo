{
    "name": "Tags de Tecnologías en Contactos",
    "summary": "Asigna automáticamente tags de tecnología a contactos según su historial de compras",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "author": "Skymedic",
    "license": "LGPL-3",
    "depends": ["contacts", "sale"],
    "data": [
        "security/ir.model.access.csv",
        "data/technology_tags_data.xml",
        "data/technology_cron.xml",
        "views/partner_technology_tag_views.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "application": False,
}
