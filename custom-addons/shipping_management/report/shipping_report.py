from odoo import fields, models
from odoo.tools.sql import SQL


class ShippingReport(models.Model):
    _name = "shipping.report"
    _description = "Análisis de envíos"
    _auto = False
    _order = "ship_date desc"
    _rec_name = "shipment_id"

    # ---- Dimensions ----
    shipment_id = fields.Many2one(
        "shipping.shipment", string="Envío", readonly=True,
    )
    picking_id = fields.Many2one(
        "stock.picking", string="Orden de entrega", readonly=True,
    )
    sale_order_id = fields.Many2one(
        "sale.order", string="Pedido de venta", readonly=True,
    )
    carrier_id = fields.Many2one(
        "delivery.carrier", string="Transportista", readonly=True,
    )
    carrier_type = fields.Char(
        string="Tipo de transportista", readonly=True,
    )
    partner_id = fields.Many2one(
        "res.partner", string="Destinatario", readonly=True,
    )
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("confirmed", "Confirmado"),
            ("in_transit", "En tránsito"),
            ("incident", "Incidencia"),
            ("delivered", "Entregado"),
            ("cancelled", "Cancelado"),
            ("returned", "Devuelto"),
        ],
        string="Estado",
        readonly=True,
    )
    company_id = fields.Many2one(
        "res.company", string="Compañía", readonly=True,
    )

    # ---- Destination ----
    country_id = fields.Many2one(
        "res.country", string="País destino", readonly=True,
    )
    state_id = fields.Many2one(
        "res.country.state", string="Provincia destino", readonly=True,
    )
    dest_city = fields.Char(string="Ciudad destino", readonly=True)
    dest_zip = fields.Char(string="CP destino", readonly=True)

    # ---- Dates ----
    ship_date = fields.Datetime(string="Fecha de envío", readonly=True)
    delivery_date = fields.Datetime(string="Fecha de entrega", readonly=True)
    ship_date_date = fields.Date(string="Fecha envío (día)", readonly=True)

    # ---- Base measures ----
    shipping_cost = fields.Float(
        string="Coste de envío", readonly=True, aggregator="sum",
    )
    number_of_packages = fields.Integer(
        string="Bultos", readonly=True, aggregator="sum",
    )
    shipping_weight = fields.Float(
        string="Peso (kg)", readonly=True, aggregator="sum",
    )
    delivery_days = fields.Float(
        string="Días de entrega", readonly=True, aggregator="avg",
    )
    is_incident = fields.Integer(
        string="Incidencias", readonly=True, aggregator="sum",
    )
    nbr = fields.Integer(
        string="Nº de envíos", readonly=True, aggregator="sum",
    )

    # ---- KPI measures ----
    sla_delivery_days = fields.Integer(
        string="Plazo SLA (días)", readonly=True, aggregator="avg",
    )
    is_on_time = fields.Integer(
        string="Entregas a tiempo", readonly=True, aggregator="sum",
    )
    is_overdue = fields.Integer(
        string="Fuera de plazo SLA", readonly=True, aggregator="sum",
    )
    is_delivered = fields.Integer(
        string="Entregados", readonly=True, aggregator="sum",
    )
    is_return = fields.Integer(
        string="Devoluciones", readonly=True, aggregator="sum",
    )

    @property
    def _table_query(self) -> SQL:
        return SQL(
            "%s %s",
            self._select(),
            self._from(),
        )

    def _select(self) -> SQL:
        return SQL("""
            SELECT
                ss.id AS id,
                ss.id AS shipment_id,
                ss.picking_id AS picking_id,
                sp.sale_id AS sale_order_id,
                ss.carrier_id AS carrier_id,
                ss.carrier_type AS carrier_type,
                ss.partner_id AS partner_id,
                ss.state AS state,
                ss.company_id AS company_id,
                rp.country_id AS country_id,
                rp.state_id AS state_id,
                rp.city AS dest_city,
                rp.zip AS dest_zip,
                ss.ship_date AS ship_date,
                ss.delivery_date AS delivery_date,
                ss.ship_date::date AS ship_date_date,
                COALESCE(ss.shipping_cost, 0) AS shipping_cost,
                COALESCE(ss.number_of_packages, 0) AS number_of_packages,
                COALESCE(sp.shipping_weight, 0) AS shipping_weight,
                CASE
                    WHEN ss.delivery_date IS NOT NULL AND ss.ship_date IS NOT NULL
                    THEN EXTRACT(EPOCH FROM (ss.delivery_date - ss.ship_date)) / 86400.0
                    ELSE 0
                END AS delivery_days,
                CASE WHEN ss.state = 'incident' THEN 1 ELSE 0 END AS is_incident,
                1 AS nbr,
                COALESCE(dc.sla_delivery_days, 3) AS sla_delivery_days,
                CASE
                    WHEN ss.state = 'delivered'
                         AND ss.delivery_date IS NOT NULL
                         AND ss.ship_date IS NOT NULL
                         AND EXTRACT(EPOCH FROM (ss.delivery_date - ss.ship_date)) / 86400.0
                             <= COALESCE(dc.sla_delivery_days, 3)
                    THEN 1 ELSE 0
                END AS is_on_time,
                CASE
                    WHEN ss.state IN ('confirmed', 'in_transit', 'incident')
                         AND ss.ship_date IS NOT NULL
                         AND (CURRENT_DATE - ss.ship_date::date)
                             > COALESCE(dc.sla_delivery_days, 3)
                    THEN 1 ELSE 0
                END AS is_overdue,
                CASE WHEN ss.state = 'delivered' THEN 1 ELSE 0 END AS is_delivered,
                CASE WHEN ss.is_return = TRUE THEN 1 ELSE 0 END AS is_return
        """)

    def _from(self) -> SQL:
        return SQL("""
            FROM shipping_shipment ss
                LEFT JOIN stock_picking sp ON sp.id = ss.picking_id
                LEFT JOIN res_partner rp ON rp.id = ss.partner_id
                LEFT JOIN delivery_carrier dc ON dc.id = ss.carrier_id
        """)
