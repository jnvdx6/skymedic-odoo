from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ShippingLabel(models.Model):
    _name = "shipping.label"
    _description = "Etiqueta de envío"
    _order = "create_date desc"
    _rec_name = "name"

    name = fields.Char(
        string="Nombre",
        compute="_compute_name",
        store=True,
    )
    shipment_id = fields.Many2one(
        "shipping.shipment",
        string="Envío",
        required=True,
        ondelete="cascade",
        index=True,
    )
    attachment_id = fields.Many2one(
        "ir.attachment",
        string="Adjunto",
        required=True,
        ondelete="cascade",
    )
    # Denormalized fields for quick list/search without joins
    carrier_id = fields.Many2one(
        related="shipment_id.carrier_id",
        store=True,
        string="Transportista",
    )
    carrier_type = fields.Selection(
        related="shipment_id.carrier_type",
        store=True,
        string="Tipo",
    )
    tracking_ref = fields.Char(
        related="shipment_id.tracking_ref",
        store=True,
        string="Nº seguimiento",
    )
    partner_id = fields.Many2one(
        related="shipment_id.partner_id",
        store=True,
        string="Destinatario",
    )
    origin = fields.Char(
        related="shipment_id.origin",
        store=True,
        string="Origen",
    )
    shipment_state = fields.Selection(
        related="shipment_id.state",
        store=True,
        string="Estado envío",
    )
    ship_date = fields.Datetime(
        related="shipment_id.ship_date",
        store=True,
        string="Fecha de envío",
    )
    company_id = fields.Many2one(
        related="shipment_id.company_id",
        store=True,
    )
    # Attachment data
    file_name = fields.Char(
        related="attachment_id.name",
        string="Archivo",
    )
    file_size = fields.Integer(
        related="attachment_id.file_size",
        string="Tamaño (bytes)",
    )
    label_type = fields.Selection(
        [
            ("shipping", "Etiqueta de envío"),
            ("return", "Etiqueta de devolución"),
            ("reprint", "Reimpresión"),
        ],
        string="Tipo de etiqueta",
        default="shipping",
    )

    @api.depends("shipment_id.name", "tracking_ref", "label_type")
    def _compute_name(self):
        type_labels = dict(self._fields["label_type"].selection)
        for label in self:
            parts = [
                label.shipment_id.name or "",
                label.tracking_ref or "",
            ]
            if label.label_type and label.label_type != "shipping":
                parts.append(type_labels.get(label.label_type, ""))
            label.name = " — ".join(filter(None, parts))

    def action_download(self):
        """Download this label's PDF."""
        self.ensure_one()
        if not self.attachment_id:
            raise UserError(
                _("No hay archivo asociado a esta etiqueta.")
            )
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{self.attachment_id.id}?download=true",
            "target": "new",
        }
