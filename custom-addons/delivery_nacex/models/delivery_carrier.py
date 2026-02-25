import base64
import hashlib
import logging

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

NACEX_API_URL = "https://pda.nacex.com/nacex_ws/ws"


class NacexDeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    delivery_type = fields.Selection(
        selection_add=[("nacex", "NACEX")],
        ondelete={"nacex": "set default"},
    )
    nacex_agency_code = fields.Char(string="Código de agencia")
    nacex_customer_code = fields.Char(string="Código de cliente")
    nacex_service_code = fields.Selection(
        [
            ("01", "NACEX 10:00H - Entrega express antes de las 10h"),
            ("02", "NACEX 12:00H - Entrega express antes de las 12h"),
            ("03", "INTERDIA - Entrega estándar día siguiente"),
            ("04", "PLUS BAG 1 - Bolsa plus tipo 1"),
            ("05", "PLUS BAG 2 - Bolsa plus tipo 2"),
            ("06", "MALETA - Transporte de equipaje"),
            ("07", "VALIJA IDA Y VUELTA - Servicio de valija ida y vuelta"),
            ("08", "NACEX 19:00H - Entrega en el día antes de las 19h"),
            ("09", "PUENTE URBANO - Servicio puente urbano"),
            ("10", "DEVOLUCIÓN ALBARÁN CLIENTE - Devolución con albarán"),
            ("11", "NACEX 08:30H - Entrega ultra-express antes de las 8:30h"),
            ("12", "DEVOLUCIÓN TALÓN - Servicio de devolución talón"),
            ("14", "DEVOLUCIÓN PLUS BAG 1 - Devolución bolsa plus tipo 1"),
            ("15", "DEVOLUCIÓN PLUS BAG 2 - Devolución bolsa plus tipo 2"),
            ("17", "DEVOLUCIÓN E-NACEX - Devolución servicio electrónico"),
            ("21", "NACEX SÁBADO - Entrega en sábado"),
            ("22", "CANARIAS - Envío estándar a Canarias"),
            ("24", "CANARIAS 24H - Envío express 24h a Canarias"),
            ("26", "PLUS PACK - Servicio plus pack"),
            ("27", "E-NACEX - Entrega económica e-commerce"),
            ("28", "PREMIUM - Entrega express premium"),
            ("29", "NX-SHOP VERDE - Punto de recogida (verde)"),
            ("30", "NX-SHOP NARANJA - Punto de recogida (naranja)"),
            ("31", "E-NACEX SHOP - E-commerce en punto de recogida"),
            ("33", "C@MBIO - Servicio de intercambio"),
            ("48", "CANARIAS 48H - Envío a Canarias en 48h"),
            ("88", "AHORA MISMO - Entrega inmediata"),
            ("90", "NACEX.SHOP - Entrega en punto NACEX.SHOP"),
            ("91", "SWAP - Servicio de intercambio directo"),
            ("95", "DEVOLUCIÓN SWAP - Devolución de intercambio"),
            ("96", "DEV. ORIGEN - Devolución a origen"),
        ],
        string="Tipo de servicio",
        help="Seleccione el tipo de servicio NACEX",
    )
    nacex_carriage_code = fields.Selection(
        [
            ("O", "Origen (pagado por el remitente)"),
            ("D", "Destino (pagado por el destinatario)"),
            ("T", "Tercera (pagado por un tercero)"),
        ],
        string="Tipo de porte",
        help="Seleccione quién paga el porte del envío",
    )
    nacex_packaging_code = fields.Selection(
        [
            ("0", "Documentos"),
            ("1", "Bolsa"),
            ("2", "Paquete"),
        ],
        string="Tipo de embalaje",
        help="Seleccione el tipo de embalaje del envío",
    )
    nacex_with_return = fields.Boolean(
        string="Con devolución",
        help="Activar envío con devolución para entregas NACEX",
    )

    def nacex_rate_shipment(self, order):
        return {
            "success": True,
            "price": 0.0,
            "error_message": False,
            "warning_message": _(
                "NACEX no proporciona estimación de tarifas."
            ),
        }

    def nacex_get_tracking_link(self, picking):
        if picking.carrier_tracking_ref:
            return (
                "https://www.nacex.com/seguimientoDetalle.do"
                f"?agencia_origen={self._nacex_get_agency_code(picking)}"
                f"&numero_albaran={picking.carrier_tracking_ref}"
            )
        return False

    def _nacex_get_agency_code(self, picking):
        agency = picking._get_carrier_agency()
        if agency and agency.external_reference:
            return agency.external_reference
        return self.nacex_agency_code or ""

    def _nacex_request(self, method, data, picking=None, account=None):
        """Execute a NACEX API request and return the response text.

        :param method: NACEX API method name (e.g. 'putExpedicion')
        :param data: dict of key/value pairs for the NACEX data parameter
        :param picking: stock.picking record (used to resolve the account)
        :param account: carrier.account record (alternative to picking)
        :return: response text
        """
        if account is None:
            account = picking._get_carrier_account()
        if not account or not account.account or not account.password:
            raise UserError(
                self.env._("Por favor configure una cuenta de transportista NACEX.")
            )
        data_str = "|".join(f"{k}={v}" for k, v in data.items())
        params = {
            "method": method,
            "data": data_str,
            "user": account.account,
            "pass": hashlib.md5(account.password.encode()).hexdigest().upper(),
        }
        _logger.info("NACEX %s request: data=%s", method, data_str)

        try:
            response = requests.get(
                NACEX_API_URL,
                params=params,
                timeout=30,
            )
        except requests.exceptions.RequestException as exc:
            raise UserError(
                self.env._(
                    "Error de conexión NACEX: %(error)s", error=exc
                )
            ) from exc

        if response.status_code not in (200, 201):
            raise UserError(
                self.env._(
                    "Error de la API NACEX (HTTP %(code)s): %(text)s",
                    code=response.status_code,
                    text=response.text,
                )
            )

        if response.text.startswith("ERROR"):
            raise UserError(
                self.env._(
                    "Error NACEX %(method)s: %(text)s",
                    method=method,
                    text=response.text,
                )
            )

        _logger.info("NACEX %s response OK", method)
        return response.text

    # ---- Expedition management ----

    def _nacex_put_expedicion(self, picking):
        """Create an expedition on NACEX and return the raw response text."""
        self.ensure_one()
        recipient = picking.partner_id
        shipper = picking.picking_type_id.warehouse_id.partner_id

        if not shipper.zip or not shipper.city or not shipper.country_id:
            raise UserError(
                self.env._("Por favor defina una dirección de remitente correcta.")
            )
        if not recipient.zip or not recipient.city or not recipient.country_id:
            raise UserError(
                self.env._("Por favor defina una dirección de destinatario correcta.")
            )

        packages = picking.move_line_ids.result_package_id
        if packages:
            package_count = str(len(packages))
            total_weight = sum(packages.mapped("shipping_weight"))
        else:
            package_count = str(picking.number_of_packages or 1)
            total_weight = picking.shipping_weight or 0.0

        data = {
            "del_cli": self._nacex_get_agency_code(picking),
            "num_cli": self.nacex_customer_code or "",
            "tip_ser": self.nacex_service_code or "",
            "tip_cob": self.nacex_carriage_code or "",
            "ref_cli": picking.origin or "",
            "tip_env": self.nacex_packaging_code or "",
            "bul": package_count,
            "kil": total_weight,
            "nom_ent": recipient.name or "",
            "dir_ent": (recipient.street or "").replace("#", " "),
            "pais_ent": recipient.country_id.code or "",
            "cp_ent": (recipient.zip or "").replace("-", "").replace("/", ""),
            "pob_ent": recipient.city or "",
            "tel_ent": recipient.phone or "",
            "obs1": "observaciones",
            "cp_rec": (shipper.zip or "").replace("-", "").replace("/", ""),
        }

        if picking.nacex_with_return:
            data["ret"] = "S"

        return self._nacex_request("putExpedicion", data, picking)

    def nacex_send_shipping(self, pickings):
        """Send shipment to NACEX and return label + tracking info."""
        self.ensure_one()
        res = []
        for picking in pickings:
            expedicion = self._nacex_put_expedicion(picking)
            parts = expedicion.split("|")

            # Store expedition code BEFORE label retrieval (for cancellation)
            picking.nacex_expedition_code = parts[0]

            tracking_number = parts[1].split("/")[1]
            label_text = self._nacex_request(
                "getEtiqueta",
                {
                    "codExp": parts[0],
                    "modelo": "PDF_B",
                },
                picking,
            )

            # Decode base64 label (NACEX uses URL-safe base64 variant)
            label_b64 = (
                label_text.replace("-", "+").replace("_", "/").replace("*", "=")
            )
            pdf_label_data = base64.b64decode(label_b64)
            picking.message_post(
                body=self.env._(
                    "<b>Número de seguimiento:</b> %(number)s",
                    number=tracking_number,
                ),
                attachments=[(f"{tracking_number}.pdf", pdf_label_data)],
            )
            res.append(
                {
                    "exact_price": 0.0,
                    "tracking_number": tracking_number,
                }
            )
        return res

    def nacex_cancel_shipment(self, pickings):
        """Cancel a shipment on NACEX using cancelExpedicion."""
        for picking in pickings:
            if not picking.nacex_expedition_code:
                raise UserError(
                    self.env._(
                        "No se puede cancelar: no se encontró código de expedición "
                        "NACEX para %(name)s.",
                        name=picking.name,
                    )
                )
            self._nacex_request(
                "cancelExpedicion",
                {"codigo": picking.nacex_expedition_code},
                picking,
            )
            picking.nacex_expedition_code = False

    # ---- Tracking ----

    def _nacex_get_info_envio(self, picking):
        """Query NACEX for shipment tracking information."""
        self.ensure_one()
        response = self._nacex_request(
            "getInfoEnvio",
            {
                "albaran": picking.carrier_tracking_ref,
                "tipo": "E",
            },
            picking,
        )
        picking.write(
            {
                "nacex_tracking_status": response,
                "nacex_tracking_status_date": fields.Datetime.now(),
            }
        )
        picking.message_post(
            body=self.env._(
                "<b>Actualización de seguimiento NACEX:</b><br/>%(status)s",
                status=response,
            ),
        )

    # ---- Address / Agency validation ----

    def _nacex_get_pueblos(self, postal_code, picking=None, account=None):
        """Validate a postal code and get city names from NACEX."""
        self.ensure_one()
        return self._nacex_request(
            "getPueblos",
            {"cp": postal_code},
            picking=picking,
            account=account,
        )

    def _nacex_get_agencia(self, postal_code, picking=None, account=None):
        """Get NACEX agency information for a postal code."""
        self.ensure_one()
        return self._nacex_request(
            "getAgencia",
            {"cp": postal_code},
            picking=picking,
            account=account,
        )

    # ---- Pickup scheduling ----

    def _nacex_put_recogida(self, picking, data):
        """Schedule a pickup with NACEX."""
        self.ensure_one()
        return self._nacex_request("putRecogida", data, picking)

    # ---- Shipping Management bridge ----

    def _nacex_update_shipment_status(self, shipment):
        """Update a shipping.shipment tracking status from NACEX API."""
        self.ensure_one()
        if not shipment.tracking_ref:
            return
        account = (
            shipment.picking_id._get_carrier_account()
            if shipment.picking_id
            else self.carrier_account_id
        )
        response = self._nacex_request(
            "getInfoEnvio",
            {"albaran": shipment.tracking_ref, "tipo": "E"},
            picking=shipment.picking_id,
            account=account,
        )
        shipment.write({
            "tracking_status_raw": response,
            "last_tracking_update": fields.Datetime.now(),
        })
        new_state = self._nacex_map_tracking_status(response)
        if new_state and new_state != shipment.state:
            shipment.write({"state": new_state})
        shipment.message_post(
            body=self.env._(
                "<b>Actualización NACEX:</b><br/>%(status)s",
                status=response,
            ),
        )

    def _nacex_map_tracking_status(self, raw_status):
        """Map NACEX raw status text to shipping.shipment state."""
        if not raw_status:
            return False
        lower = raw_status.lower()
        if "entregado" in lower or "delivered" in lower:
            return "delivered"
        if any(
            kw in lower
            for kw in ("tránsito", "transito", "transit", "reparto")
        ):
            return "in_transit"
        if "devuelto" in lower or "returned" in lower:
            return "returned"
        return False

    def _nacex_reprint_shipment_label(self, shipment):
        """Re-fetch and attach a NACEX label to the shipment."""
        self.ensure_one()
        if not shipment.expedition_code:
            raise UserError(
                self.env._(
                    "No hay código de expedición para reimprimir la etiqueta."
                )
            )
        account = (
            shipment.picking_id._get_carrier_account()
            if shipment.picking_id
            else self.carrier_account_id
        )
        label_text = self._nacex_request(
            "getEtiqueta",
            {"codExp": shipment.expedition_code, "modelo": "PDF_B"},
            picking=shipment.picking_id,
            account=account,
        )
        label_b64 = (
            label_text.replace("-", "+").replace("_", "/").replace("*", "=")
        )
        pdf_data = base64.b64decode(label_b64)
        attachment = self.env["ir.attachment"].create({
            "name": f"{shipment.tracking_ref or shipment.name}_reprint.pdf",
            "type": "binary",
            "datas": base64.b64encode(pdf_data),
            "res_model": "shipping.shipment",
            "res_id": shipment.id,
            "mimetype": "application/pdf",
        })
        # Create shipping.label record if the model is available
        if "shipping.label" in self.env:
            self.env["shipping.label"].create({
                "shipment_id": shipment.id,
                "attachment_id": attachment.id,
                "label_type": "reprint",
            })
        shipment.message_post(
            body=self.env._(
                "Etiqueta reimpresa para %(ref)s",
                ref=shipment.tracking_ref or shipment.name,
            ),
        )

    # ---- Test connection ----

    def nacex_action_test_connection(self):
        """Test the NACEX API connection using getPueblos."""
        self.ensure_one()
        account = self.carrier_account_id
        if not account:
            raise UserError(
                self.env._(
                    "Por favor configure primero una cuenta de transportista NACEX."
                )
            )
        self._nacex_get_pueblos("28001", account=account)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": self.env._("Conexión exitosa"),
                "message": self.env._(
                    "Conexión exitosa con la API de NACEX."
                ),
                "type": "success",
                "sticky": False,
            },
        }
