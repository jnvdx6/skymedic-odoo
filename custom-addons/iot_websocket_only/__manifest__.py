{
    "name": "IoT Websocket Only",
    "version": "19.0.1.0.0",
    "category": "Internet of Things (IoT)",
    "summary": "Force IoT communication through server websocket (skip WebRTC and longpolling)",
    "description": """
        Forces all IoT Box communication to go through the Odoo server's
        bus.bus websocket channel, bypassing direct browser-to-IoT-box
        connections (WebRTC and longpolling).

        This is required when the IoT Box is on a different network
        (e.g., connected via Tailscale VPN) and the user's browser
        cannot reach the IoT Box IP directly.
    """,
    "author": "Skymedic",
    "depends": ["iot"],
    "assets": {
        "web.assets_backend": [
            "iot_websocket_only/static/src/iot_http_service_patch.js",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
