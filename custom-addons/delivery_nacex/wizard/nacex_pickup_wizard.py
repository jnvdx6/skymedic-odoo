# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class NacexPickupWizard(models.TransientModel):
    _name = "nacex.pickup.wizard"
    _description = "Asistente de programación de recogida NACEX"

    picking_id = fields.Many2one(
        "stock.picking",
        string="Orden de entrega",
        required=True,
    )
    reco_codigo = fields.Char(
        string="Código de recogida",
        required=True,
    )
    del_sol = fields.Char(
        string="Código de agencia",
        required=True,
    )
    num_rec = fields.Char(
        string="Número de recogida",
    )
    ref = fields.Char(
        string="Referencia",
    )
    pickup_date = fields.Date(
        string="Fecha de recogida",
        required=True,
        default=fields.Date.today,
    )

    def action_schedule_pickup(self):
        """Schedule a pickup via NACEX API."""
        self.ensure_one()
        picking = self.picking_id
        carrier = picking.carrier_id
        data = {
            "reco_codigo": self.reco_codigo,
            "Del_Sol": self.del_sol,
        }
        if self.num_rec:
            data["Num_Rec"] = self.num_rec
        if self.ref:
            data["ref"] = self.ref
        result = carrier._nacex_put_recogida(picking, data)
        picking.message_post(
            body=self.env._(
                "<b>Recogida NACEX programada:</b><br/>%(result)s",
                result=result,
            ),
        )
        return {"type": "ir.actions.act_window_close"}
