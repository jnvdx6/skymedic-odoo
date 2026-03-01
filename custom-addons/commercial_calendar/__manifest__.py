{
    "name": "Calendario Comercial",
    "summary": "Actividades comerciales integradas con calendario y contactos",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "author": "Skymedic",
    "website": "https://skymedic.es",
    "license": "AGPL-3",
    "depends": [
        "calendar",
        "contacts",
        "sale",
    ],
    "data": [
        "security/commercial_calendar_security.xml",
        "data/commercial_activity_type_data.xml",
        "data/calendar_event_type_data.xml",
        "data/commercial_cron_data.xml",
        "views/calendar_event_views.xml",
        "views/res_partner_views.xml",
        "views/commercial_calendar_menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "commercial_calendar/static/src/**/*",
        ],
    },
    "installable": True,
    "application": False,
}
