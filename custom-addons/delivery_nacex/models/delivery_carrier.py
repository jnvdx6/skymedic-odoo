import base64
import hashlib
import logging

import requests
from markupsafe import Markup

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

NACEX_API_URL = "https://pda.nacex.com/nacex_ws/ws"

# Canary Islands postal code prefixes (35xxx = Las Palmas, 38xxx = Tenerife)
_CANARIAS_CP_PREFIXES = ("35", "38")


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
    nacex_min_weight = fields.Float(
        string="Peso mínimo (kg)",
        default=0.5,
        help="Peso mínimo a enviar a NACEX cuando no se ha definido peso en el albarán",
    )
    nacex_send_customer_email = fields.Boolean(
        string="Enviar email al cliente",
        default=True,
        help="Enviar email automático al cliente con información de seguimiento",
    )
    nacex_validate_address = fields.Boolean(
        string="Validar dirección",
        default=True,
        help="Validar el código postal del destinatario con NACEX antes de crear la expedición",
    )

    def nacex_rate_shipment(self, order):
        """Estimate shipping cost via NACEX getValoracion."""
        partner = order.partner_shipping_id or order.partner_id
        shipper_zip = (
            order.warehouse_id.partner_id.zip or ""
        ).replace("-", "").replace("/", "")
        dest_zip = (partner.zip or "").replace("-", "").replace("/", "")
        if not shipper_zip or not dest_zip or not self.nacex_service_code:
            return {
                "success": True,
                "price": 0.0,
                "error_message": False,
                "warning_message": False,
            }
        try:
            account = self.carrier_account_id
            response = self._nacex_request(
                "getValoracion",
                {
                    "cp_rec": shipper_zip,
                    "cp_ent": dest_zip,
                    "tip_ser": self.nacex_service_code,
                    "tip_env": self.nacex_packaging_code or "2",
                    "kil": str(
                        order.order_line.filtered(
                            lambda l: not l.is_delivery
                        ).mapped("product_id.weight")
                        and sum(
                            l.product_id.weight * l.product_uom_qty
                            for l in order.order_line
                            if not l.is_delivery and l.product_id.weight
                        )
                        or self.nacex_min_weight or 1
                    ),
                    "del_cli": self.nacex_agency_code or "",
                    "num_cli": self.nacex_customer_code or "",
                },
                account=account,
            )
            parts = response.split("|")
            price = float(parts[1].replace(",", ".")) if len(parts) > 1 else 0.0
            return {
                "success": True,
                "price": price,
                "error_message": False,
                "warning_message": False,
            }
        except (UserError, ValueError, IndexError):
            return {
                "success": True,
                "price": 0.0,
                "error_message": False,
                "warning_message": False,
            }

    # ---- Tracking URL ----

    def nacex_get_tracking_link(self, picking):
        if picking.carrier_tracking_ref:
            return self._nacex_tracking_url(
                self._nacex_get_agency_code(picking),
                picking.carrier_tracking_ref,
            )
        return False

    def _nacex_tracking_url(self, agency_code, tracking_ref):
        """Build the full NACEX tracking URL."""
        return (
            "https://www.nacex.com/seguimientoDetalle.do"
            f"?agencia_origen={agency_code}"
            f"&numero_albaran={tracking_ref}"
            "&externo=N"
        )

    # ---- Helpers ----

    def _nacex_get_agency_code(self, picking):
        agency = picking._get_carrier_agency()
        if agency and agency.external_reference:
            return agency.external_reference
        return self.nacex_agency_code or ""

    def _nacex_service_label(self):
        """Return the human-readable label of the current service code."""
        return dict(
            self._fields["nacex_service_code"].selection
        ).get(self.nacex_service_code, self.nacex_service_code or "")

    @staticmethod
    def _nacex_is_canarias(postal_code):
        """Check if a postal code belongs to the Canary Islands."""
        cp = (postal_code or "").strip()
        return cp[:2] in _CANARIAS_CP_PREFIXES

    @staticmethod
    def _nacex_decode_label(label_text):
        """Decode a NACEX base64 label (URL-safe variant) to binary PDF."""
        label_b64 = (
            label_text.replace("-", "+").replace("_", "/").replace("*", "=")
        )
        return base64.b64decode(label_b64)

    def _nacex_get_weight(self, picking):
        """Compute the shipping weight, applying minimum weight if needed."""
        packages = picking.move_line_ids.result_package_id
        if packages:
            weight = sum(packages.mapped("shipping_weight"))
        else:
            weight = picking.shipping_weight or 0.0
        min_weight = self.nacex_min_weight or 0.0
        return max(weight, min_weight) if min_weight else weight

    def _nacex_get_package_count(self, picking):
        """Compute the number of packages."""
        packages = picking.move_line_ids.result_package_id
        if packages:
            return len(packages)
        return picking.number_of_packages or 1

    # ---- API communication ----

    def _nacex_request(self, method, data, picking=None, account=None):
        """Execute a NACEX API request and return the response text."""
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

    # ---- Address validation ----

    def _nacex_validate_recipient(self, picking):
        """Validate recipient postal code against NACEX before shipping."""
        if not self.nacex_validate_address:
            return
        recipient = picking.partner_id
        cp = (recipient.zip or "").replace("-", "").replace("/", "")
        if not cp:
            return
        try:
            result = self._nacex_request(
                "getPueblos", {"cp": cp}, picking,
            )
        except UserError:
            _logger.warning(
                "NACEX address validation failed for CP %s, skipping", cp,
            )
            return
        # result is "CITY_NAME" or "CITY1\nCITY2" for ambiguous CPs
        if not result:
            return
        nacex_cities = [c.strip().upper() for c in result.split("\n") if c.strip()]
        recipient_city = (recipient.city or "").strip().upper()
        if recipient_city and nacex_cities and recipient_city not in nacex_cities:
            _logger.info(
                "NACEX city mismatch: recipient=%s, NACEX=%s (CP=%s)",
                recipient_city, nacex_cities, cp,
            )
            picking.message_post(body=Markup(
                "<b>Aviso NACEX:</b> La ciudad del destinatario "
                "(<i>{city}</i>) no coincide exactamente con la respuesta "
                "de NACEX para el CP {cp}: <i>{nacex_cities}</i>. "
                "El envío se ha procesado igualmente."
            ).format(
                city=recipient_city,
                cp=cp,
                nacex_cities=", ".join(nacex_cities),
            ))

    # ---- Expedition management ----

    def _nacex_build_expedition_data(self, picking):
        """Build the data dict for a putExpedicion call."""
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

        package_count = self._nacex_get_package_count(picking)
        total_weight = self._nacex_get_weight(picking)

        # Build full address: street + street2
        address_parts = [recipient.street or ""]
        if recipient.street2:
            address_parts.append(recipient.street2)
        full_address = ", ".join(p for p in address_parts if p).replace("#", " ")

        # Build observations from picking note or sale order note
        obs = ""
        if picking.note:
            obs = str(picking.note).strip()[:60]
        elif picking.sale_id and picking.sale_id.note:
            obs = str(picking.sale_id.note).strip()[:60]

        recipient_cp = (recipient.zip or "").replace("-", "").replace("/", "")

        data = {
            "del_cli": self._nacex_get_agency_code(picking),
            "num_cli": self.nacex_customer_code or "",
            "tip_ser": self.nacex_service_code or "",
            "tip_cob": self.nacex_carriage_code or "",
            "ref_cli": picking.origin or picking.name,
            "tip_env": self.nacex_packaging_code or "",
            "bul": str(package_count),
            "kil": total_weight,
            "nom_ent": recipient.name or "",
            "dir_ent": full_address,
            "pais_ent": recipient.country_id.code or "",
            "cp_ent": recipient_cp,
            "pob_ent": recipient.city or "",
            "tel_ent": recipient.phone or recipient.mobile or "",
            "obs1": obs,
            "cp_rec": (shipper.zip or "").replace("-", "").replace("/", ""),
        }

        if picking.nacex_with_return:
            data["ret"] = "S"

        return data

    def _nacex_put_expedicion(self, picking):
        """Create an expedition on NACEX and return the raw response text."""
        data = self._nacex_build_expedition_data(picking)
        return self._nacex_request("putExpedicion", data, picking)

    def _nacex_put_aduana(self, picking, expedition_code):
        """Submit customs data via putAduana for Canary Islands / international.

        Called after putExpedicion when the destination requires customs
        processing (Canary Islands postal codes 35xxx/38xxx).
        """
        recipient = picking.partner_id
        shipper = picking.picking_type_id.warehouse_id.partner_id
        agency_code = self._nacex_get_agency_code(picking)
        customer_code = self.nacex_customer_code or ""
        data = {
            "expe_codigo": expedition_code,
            "valor_mer": "1",
            "tipo_mer": "M",
            "tipo_exp": "D",
            "nif_origen": shipper.vat or shipper.company_id.vat or "",
            "nif_destino": recipient.vat or "",
            "del_cli_ori": agency_code,
            "num_cli_ori": customer_code,
            "del_cli_dest": agency_code,
            "num_cli_dest": customer_code,
            "del_cli_imp": agency_code,
            "num_cli_imp": customer_code,
        }
        try:
            self._nacex_request("putAduana", data, picking)
            _logger.info(
                "NACEX putAduana OK for expedition %s", expedition_code,
            )
        except UserError:
            _logger.warning(
                "NACEX putAduana failed for expedition %s, "
                "customs may need manual processing",
                expedition_code,
                exc_info=True,
            )

    def nacex_send_shipping(self, pickings):
        """Send shipment to NACEX and return label + tracking info."""
        self.ensure_one()
        res = []
        for picking in pickings:
            # Validate address before creating expedition
            self._nacex_validate_recipient(picking)

            expedicion = self._nacex_put_expedicion(picking)
            parts = expedicion.split("|")

            # Store expedition code BEFORE label retrieval (for cancellation)
            expedition_code = parts[0]
            picking.nacex_expedition_code = expedition_code

            tracking_number = parts[1].split("/")[1]
            agency_code = self._nacex_get_agency_code(picking)
            tracking_url = self._nacex_tracking_url(agency_code, tracking_number)

            # Canary Islands: submit customs data via putAduana
            recipient_cp = (picking.partner_id.zip or "").replace(
                "-", ""
            ).replace("/", "")
            if self._nacex_is_canarias(recipient_cp):
                self._nacex_put_aduana(picking, expedition_code)

            # Fetch PDF label from NACEX
            label_text = self._nacex_request(
                "getEtiqueta",
                {"codExp": expedition_code, "modelo": "PDF_B"},
                picking,
            )
            pdf_label_data = self._nacex_decode_label(label_text)

            # Create attachment directly on the picking so delivery_iot can
            # find it via 'name ILIKE Label%' + res_model=stock.picking
            label_name = f"LabelNacex-{tracking_number}.pdf"
            self.env["ir.attachment"].create({
                "name": label_name,
                "type": "binary",
                "datas": base64.b64encode(pdf_label_data),
                "res_model": "stock.picking",
                "res_id": picking.id,
                "mimetype": "application/pdf",
            })

            service_label = self._nacex_service_label()
            recipient = picking.partner_id
            n_packages = self._nacex_get_package_count(picking)
            weight = self._nacex_get_weight(picking)

            # Rich HTML message on picking chatter
            picking.message_post(body=Markup(
                "<b>Envío NACEX creado</b><br/>"
                "<b>Servicio:</b> {service}<br/>"
                "<b>Expedición:</b> {expedition}<br/>"
                "<b>N.º seguimiento:</b> "
                "<a href=\"{url}\" target=\"_blank\">{tracking}</a><br/>"
                "<b>Bultos:</b> {packages} — <b>Peso:</b> {weight} kg<br/>"
                "<b>Destinatario:</b> {partner} — {city} ({zip})"
            ).format(
                service=service_label,
                expedition=expedition_code,
                url=tracking_url,
                tracking=tracking_number,
                packages=n_packages,
                weight=weight,
                partner=recipient.name or "",
                city=recipient.city or "",
                zip=recipient.zip or "",
            ))

            # Notify the originating sale order
            self._nacex_notify_sale_order(
                picking, tracking_number, tracking_url, service_label,
            )

            # Send email to customer
            self._nacex_send_customer_email(
                picking, tracking_number, tracking_url, service_label,
            )

            # Get real shipping price from NACEX
            exact_price = self._nacex_get_shipping_price(picking)

            res.append({
                "exact_price": exact_price,
                "tracking_number": tracking_number,
            })
        return res

    def _nacex_notify_sale_order(
        self, picking, tracking_number, tracking_url, service_label,
    ):
        """Post a shipping notification on the linked sale order."""
        sale = picking.sale_id
        if not sale:
            return
        now_str = fields.Datetime.now().strftime("%d/%m/%Y %H:%M")
        sale.message_post(body=Markup(
            "<b>Envío NACEX generado desde {picking}</b><br/>"
            "<b>Servicio:</b> {service}<br/>"
            "<b>Seguimiento:</b> "
            "<a href=\"{url}\" target=\"_blank\">{tracking}</a><br/>"
            "<b>Fecha:</b> {date}"
        ).format(
            picking=picking.name,
            service=service_label,
            url=tracking_url,
            tracking=tracking_number,
            date=now_str,
        ))

    def _nacex_send_customer_email(
        self, picking, tracking_number, tracking_url, service_label,
    ):
        """Send a tracking email to the customer."""
        if not self.nacex_send_customer_email:
            return
        partner = picking.partner_id
        if not partner.email:
            _logger.info(
                "No email for partner %s, skipping NACEX notification",
                partner.name,
            )
            return
        template = self.env.ref(
            "delivery_nacex.nacex_shipping_email_template",
            raise_if_not_found=False,
        )
        if not template:
            _logger.warning("NACEX email template not found, skipping")
            return
        template.with_context(
            tracking_number=tracking_number,
            tracking_url=tracking_url,
            service_label=service_label,
        ).send_mail(picking.id, force_send=True)

    def _nacex_get_shipping_price(self, picking):
        """Estimate the shipping price via getValoracion for a picking."""
        shipper = picking.picking_type_id.warehouse_id.partner_id
        recipient = picking.partner_id
        shipper_zip = (shipper.zip or "").replace("-", "").replace("/", "")
        dest_zip = (recipient.zip or "").replace("-", "").replace("/", "")
        weight = self._nacex_get_weight(picking) or 1
        try:
            response = self._nacex_request(
                "getValoracion",
                {
                    "cp_rec": shipper_zip,
                    "cp_ent": dest_zip,
                    "tip_ser": self.nacex_service_code or "",
                    "tip_env": self.nacex_packaging_code or "2",
                    "kil": str(weight),
                    "del_cli": self.nacex_agency_code or "",
                    "num_cli": self.nacex_customer_code or "",
                },
                picking,
            )
            parts = response.split("|")
            return float(parts[1].replace(",", ".")) if len(parts) > 1 else 0.0
        except (UserError, ValueError, IndexError):
            _logger.warning(
                "NACEX getValoracion failed for %s, returning 0", picking.name,
            )
            return 0.0

    # ---- Return label ----

    def nacex_get_return_label(self, picking, tracking_number=None, origin=None):
        """Generate a return label by creating a reverse expedition."""
        self.ensure_one()
        recipient = picking.partner_id
        shipper = picking.picking_type_id.warehouse_id.partner_id

        # For return: swap sender and recipient
        cp_origin = (recipient.zip or "").replace("-", "").replace("/", "")
        address_parts = [recipient.street or ""]
        if recipient.street2:
            address_parts.append(recipient.street2)
        full_address = ", ".join(p for p in address_parts if p).replace("#", " ")

        data = {
            "del_cli": self._nacex_get_agency_code(picking),
            "num_cli": self.nacex_customer_code or "",
            "tip_ser": self.nacex_service_code or "",
            "tip_cob": self.nacex_carriage_code or "",
            "ref_cli": f"DEV-{picking.origin or picking.name}",
            "tip_env": self.nacex_packaging_code or "",
            "bul": "1",
            "kil": self._nacex_get_weight(picking),
            # Sender = original recipient (customer)
            "nom_rec": recipient.name or "",
            "dir_rec": full_address,
            "pais_rec": recipient.country_id.code or "",
            "cp_rec": cp_origin,
            "pob_rec": recipient.city or "",
            "tel_rec": recipient.phone or recipient.mobile or "",
            # Recipient = warehouse (us)
            "nom_ent": shipper.name or "",
            "dir_ent": (shipper.street or "").replace("#", " "),
            "pais_ent": shipper.country_id.code or "",
            "cp_ent": (shipper.zip or "").replace("-", "").replace("/", ""),
            "pob_ent": shipper.city or "",
            "tel_ent": shipper.phone or shipper.mobile or "",
            "obs1": f"Devolución {picking.name}",
        }

        result = self._nacex_request("putExpedicion", data, picking)
        parts = result.split("|")
        ret_expedition = parts[0]
        ret_tracking = parts[1].split("/")[1]

        # Fetch return label
        label_text = self._nacex_request(
            "getEtiqueta",
            {"codExp": ret_expedition, "modelo": "PDF_B"},
            picking,
        )
        pdf_data = self._nacex_decode_label(label_text)

        # Attach to picking
        label_name = f"LabelNacex-RETURN-{ret_tracking}.pdf"
        self.env["ir.attachment"].create({
            "name": label_name,
            "type": "binary",
            "datas": base64.b64encode(pdf_data),
            "res_model": "stock.picking",
            "res_id": picking.id,
            "mimetype": "application/pdf",
        })

        ret_url = self._nacex_tracking_url(
            self._nacex_get_agency_code(picking), ret_tracking,
        )
        picking.message_post(body=Markup(
            "<b>Etiqueta de DEVOLUCIÓN NACEX creada</b><br/>"
            "<b>Expedición:</b> {expedition}<br/>"
            "<b>Seguimiento:</b> "
            "<a href=\"{url}\" target=\"_blank\">{tracking}</a>"
        ).format(
            expedition=ret_expedition,
            url=ret_url,
            tracking=ret_tracking,
        ))
        return ret_tracking

    # ---- Cancel ----

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
                {"expe_codigo": picking.nacex_expedition_code},
                picking,
            )
            picking.nacex_expedition_code = False

    # ---- Tracking ----

    def _nacex_get_info_envio(self, picking):
        """Query NACEX for shipment tracking information.

        Uses getEstadoExpedicion for current status and
        getHistoricoExpedicion for the full event history.
        """
        self.ensure_one()
        if not picking.nacex_expedition_code:
            raise UserError(
                self.env._(
                    "No hay código de expedición NACEX para consultar el estado."
                )
            )
        # Current status (getEstadoExpedicion)
        status_resp = self._nacex_request(
            "getEstadoExpedicion",
            {"expe_codigo": picking.nacex_expedition_code},
            picking,
        )
        current_status, raw_status = self._nacex_parse_estado(status_resp)

        # Full history (getHistoricoExpedicion)
        history_resp = self._nacex_request(
            "getHistoricoExpedicion",
            {"codexp": picking.nacex_expedition_code},
            picking,
        )
        lines, html_history = self._nacex_parse_historico(history_resp)
        status_text = "\n".join(lines) if lines else current_status

        tracking_url = self.nacex_get_tracking_link(picking)
        picking.write({
            "nacex_tracking_status": status_text,
            "nacex_tracking_status_date": fields.Datetime.now(),
        })
        picking.message_post(body=Markup(
            "<b>Estado actual NACEX:</b> {status}<br/>"
            "<b>N.º seguimiento:</b> "
            "<a href=\"{url}\" target=\"_blank\">{tracking}</a><br/>"
            "<b>Historial:</b>{history}"
        ).format(
            status=current_status,
            url=tracking_url or "",
            tracking=picking.carrier_tracking_ref or "",
            history=Markup(html_history),
        ))

        # Notify commercial and logistics on incident
        if raw_status == "INCIDENCIA":
            self._nacex_notify_incident(picking, current_status, tracking_url)

    @staticmethod
    def _nacex_parse_estado(response):
        """Parse getEstadoExpedicion response into a human-readable status.

        Response format: codExp|date|time|obs|STATUS|code|agency|albaran|...
        STATUS is one of: OK, RECOGIDO, TRANSITO, REPARTO, INCIDENCIA
        Returns (human_label, raw_status_code).
        """
        status_labels = {
            "OK": "Entregada",
            "RECOGIDO": "Recogida",
            "TRANSITO": "En tránsito",
            "REPARTO": "En reparto",
            "INCIDENCIA": "Incidencia",
        }
        parts = response.split("|")
        if len(parts) >= 5:
            raw = parts[4].strip()
            return status_labels.get(raw, raw), raw
        return response, ""

    @staticmethod
    def _nacex_parse_historico(response):
        """Parse getHistoricoExpedicion into text lines and HTML.

        Response format: date~time~description~agency | date~time~...
        Returns (lines_list, html_string).
        """
        entries = response.split("|")
        lines = []
        for entry in entries:
            fields = [f.strip() for f in entry.split("~")]
            if len(fields) >= 3:
                date_str, time_str, desc = fields[0], fields[1], fields[2]
                location = fields[3] if len(fields) > 3 else ""
                line = f"{date_str} {time_str} — {desc}"
                if location:
                    line += f" ({location})"
                lines.append(line)
        html_items = "".join(
            f'<li style="margin:2px 0;">{line}</li>' for line in lines
        )
        html = (
            f'<ul style="margin:5px 0;padding-left:20px;">{html_items}</ul>'
            if html_items else ""
        )
        return lines, html

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
        expedition_code = (
            shipment.expedition_code
            or (shipment.picking_id and shipment.picking_id.nacex_expedition_code)
        )
        if not expedition_code:
            return
        account = (
            shipment.picking_id._get_carrier_account()
            if shipment.picking_id
            else self.carrier_account_id
        )
        # Current status
        status_resp = self._nacex_request(
            "getEstadoExpedicion",
            {"expe_codigo": expedition_code},
            picking=shipment.picking_id,
            account=account,
        )
        current_status, raw_status = self._nacex_parse_estado(status_resp)

        # Full history
        history_resp = self._nacex_request(
            "getHistoricoExpedicion",
            {"codexp": expedition_code},
            picking=shipment.picking_id,
            account=account,
        )
        lines, html_history = self._nacex_parse_historico(history_resp)
        status_text = "\n".join(lines) if lines else current_status

        shipment.write({
            "tracking_status_raw": status_text,
            "last_tracking_update": fields.Datetime.now(),
        })
        new_state = self._nacex_map_tracking_status(current_status)
        if new_state and new_state != shipment.state:
            shipment.write({"state": new_state})
        shipment.message_post(body=Markup(
            "<b>Actualización NACEX:</b> {status}<br/>{history}"
        ).format(
            status=current_status,
            history=Markup(html_history),
        ))

        # Notify commercial and logistics on incident
        if raw_status == "INCIDENCIA" and shipment.picking_id:
            tracking_url = self.nacex_get_tracking_link(shipment.picking_id)
            self._nacex_notify_incident(
                shipment.picking_id, current_status, tracking_url,
            )

    def _nacex_map_tracking_status(self, parsed_status):
        """Map parsed NACEX status to shipping.shipment state.

        Input comes from _nacex_parse_estado: Entregada, Recogida,
        En tránsito, En reparto, Incidencia.
        """
        if not parsed_status:
            return False
        lower = parsed_status.lower()
        if "entregad" in lower:
            return "delivered"
        if "incidencia" in lower:
            return "incident"
        if any(kw in lower for kw in ("tránsito", "reparto", "recogid")):
            return "in_transit"
        if "devuelto" in lower or "returned" in lower:
            return "returned"
        return False

    def _nacex_notify_incident(self, picking, status_label, tracking_url):
        """Notify commercial (salesperson) and logistics when NACEX reports INCIDENCIA.

        Sends an internal notification via message_notify to:
        - The salesperson on the linked sale order (commercial team)
        - All users in the stock.group_stock_manager group (logistics team)
        """
        partner_ids = set()

        # 1. Salesperson from the sale order (commercial)
        sale = picking.sale_id
        if sale and sale.user_id and sale.user_id.partner_id:
            partner_ids.add(sale.user_id.partner_id.id)

        # 2. Logistics: all stock managers
        stock_mgr_group = self.env.ref(
            "stock.group_stock_manager", raise_if_not_found=False,
        )
        if stock_mgr_group:
            for user in stock_mgr_group.users:
                if user.active and user.partner_id:
                    partner_ids.add(user.partner_id.id)

        if not partner_ids:
            return

        recipient = picking.partner_id
        body = Markup(
            "<b>⚠ INCIDENCIA NACEX</b><br/>"
            "<b>Albarán:</b> {picking}<br/>"
            "<b>Pedido:</b> {order}<br/>"
            "<b>Destinatario:</b> {partner} — {city} ({zip})<br/>"
            "<b>Estado:</b> {status}<br/>"
            "<b>Seguimiento:</b> "
            "<a href=\"{url}\" target=\"_blank\">{tracking}</a>"
        ).format(
            picking=picking.name,
            order=sale.name if sale else "-",
            partner=recipient.name or "",
            city=recipient.city or "",
            zip=recipient.zip or "",
            status=status_label,
            url=tracking_url or "",
            tracking=picking.carrier_tracking_ref or "",
        )

        picking.message_notify(
            partner_ids=list(partner_ids),
            body=body,
            subject=f"⚠ Incidencia NACEX — {picking.name}",
        )
        _logger.info(
            "NACEX incident notification sent for %s to %d recipients",
            picking.name, len(partner_ids),
        )

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
        pdf_data = self._nacex_decode_label(label_text)
        label_name = f"LabelNacex-{shipment.tracking_ref or shipment.name}_reprint.pdf"
        attachment = self.env["ir.attachment"].create({
            "name": label_name,
            "type": "binary",
            "datas": base64.b64encode(pdf_data),
            "res_model": "shipping.shipment",
            "res_id": shipment.id,
            "mimetype": "application/pdf",
        })
        # Also create on the picking for IoT printing
        if shipment.picking_id:
            self.env["ir.attachment"].create({
                "name": label_name,
                "type": "binary",
                "datas": base64.b64encode(pdf_data),
                "res_model": "stock.picking",
                "res_id": shipment.picking_id.id,
                "mimetype": "application/pdf",
            })
        if "shipping.label" in self.env:
            self.env["shipping.label"].create({
                "shipment_id": shipment.id,
                "attachment_id": attachment.id,
                "label_type": "reprint",
            })
        shipment.message_post(body=Markup(
            "Etiqueta reimpresa para <b>{ref}</b>"
        ).format(ref=shipment.tracking_ref or shipment.name))

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
