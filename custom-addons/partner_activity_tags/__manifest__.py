{
    "name": "Tags de Actividad de Compra en Contactos",
    "summary": "Clasifica automáticamente contactos según la antigüedad de su última compra",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "author": "Skymedic",
    "license": "LGPL-3",
    "depends": ["contacts", "sale"],
    "data": [
        "security/ir.model.access.csv",
        "data/activity_tags_data.xml",
        "data/activity_cron.xml",
        "views/partner_activity_tag_views.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "application": False,
}
