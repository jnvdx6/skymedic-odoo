{
    "name": "Tags de Línea de Producto en Contactos",
    "summary": "Clasifica contactos según las líneas de producto que compran",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "author": "Skymedic",
    "license": "LGPL-3",
    "depends": ["contacts", "sale"],
    "data": [
        "security/ir.model.access.csv",
        "data/product_line_tags_data.xml",
        "data/product_line_cron.xml",
        "views/partner_product_line_tag_views.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "application": False,
}
