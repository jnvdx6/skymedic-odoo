from odoo import fields, models


class CommercialFollowupRule(models.Model):
    _name = 'commercial.followup.rule'
    _description = 'Regla de Seguimiento Comercial'
    _order = 'sequence, id'

    name = fields.Char(string='Nombre', required=True)
    active = fields.Boolean(string='Activo', default=True)
    sequence = fields.Integer(string='Secuencia', default=10)
    trigger_activity_type_id = fields.Many2one(
        'mail.activity.type',
        string='Cuando se completa',
        required=True,
        domain="[('category', '=', 'meeting'), ('res_model', '=', 'res.partner')]",
        help="Tipo de actividad que al completarse dispara esta regla.",
    )
    followup_activity_type_id = fields.Many2one(
        'mail.activity.type',
        string='Programar actividad',
        required=True,
        domain="[('category', '=', 'meeting'), ('res_model', '=', 'res.partner')]",
        help="Tipo de actividad de seguimiento a crear.",
    )
    delay_days = fields.Integer(
        string='Días después',
        required=True,
        default=7,
    )
    auto_create_event = fields.Boolean(
        string='Crear evento en calendario',
        default=True,
    )
    summary_template = fields.Char(
        string='Resumen',
        help="Resumen del seguimiento. Use {partner} para el nombre del contacto.",
    )
    note_template = fields.Html(
        string='Nota',
        help="Plantilla de la nota del seguimiento.",
    )
