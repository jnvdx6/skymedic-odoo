import logging
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CommercialQuickLog(models.TransientModel):
    _name = 'commercial.quick.log'
    _description = 'Registro Rápido de Actividad Comercial'

    # --- Individual mode ---
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
    )
    activity_type_id = fields.Many2one(
        'mail.activity.type',
        string='Tipo de Actividad',
        domain="[('category', '=', 'meeting'), ('res_model', '=', 'res.partner')]",
    )
    date = fields.Datetime(
        string='Fecha',
        default=fields.Datetime.now,
    )
    feedback = fields.Text(
        string='Notas',
    )

    # --- Batch mode ---
    mode = fields.Selection(
        [('single', 'Individual'), ('batch', 'Lote')],
        string='Modo',
        default='single',
    )
    line_ids = fields.One2many(
        'commercial.quick.log.line',
        'wizard_id',
        string='Registros',
    )

    def action_log_single(self):
        """Register a single activity: create completed event + trigger follow-ups."""
        self.ensure_one()
        if not self.partner_id or not self.activity_type_id:
            raise UserError(_("Selecciona un cliente y un tipo de actividad."))
        self._create_completed_event(
            self.partner_id,
            self.activity_type_id,
            self.date or fields.Datetime.now(),
            self.feedback,
        )
        return {'type': 'ir.actions.act_window_close'}

    def action_log_batch(self):
        """Register multiple activities at once."""
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("Añade al menos un registro."))
        for line in self.line_ids:
            if not line.partner_id or not line.activity_type_id:
                continue
            self._create_completed_event(
                line.partner_id,
                line.activity_type_id,
                line.date or fields.Datetime.now(),
                line.feedback,
            )
        return {'type': 'ir.actions.act_window_close'}

    def _create_completed_event(self, partner, activity_type, date_time, feedback):
        """Create a calendar event marked as completed and trigger follow-ups."""
        CalendarEvent = self.env['calendar.event']
        partner_model_id = self.env['ir.model']._get_id('res.partner')

        # Create the calendar event (auto-creates linked activity via calendar_event.create)
        event = CalendarEvent.create({
            'name': '%s - %s' % (activity_type.name, partner.name),
            'start': date_time,
            'stop': fields.Datetime.to_string(
                fields.Datetime.from_string(str(date_time)) + timedelta(hours=1)
            ),
            'commercial_activity_type_id': activity_type.id,
            'commercial_partner_id': partner.id,
            'commercial_feedback': feedback or '',
            'user_id': self.env.uid,
            'partner_ids': [(4, self.env.user.partner_id.id), (4, partner.id)],
        })

        # Find the linked activity and mark it as done (triggers follow-ups)
        activities = self.env['mail.activity'].search([
            ('calendar_event_id', '=', event.id),
            ('res_model', '=', 'res.partner'),
            ('res_id', '=', partner.id),
        ])
        if activities:
            activities._action_done(feedback=feedback or '')
        else:
            # No linked activity was created — create follow-ups directly
            followup_data = [{
                'trigger_type_id': activity_type.id,
                'partner_id': partner.id,
                'user_id': self.env.uid,
            }]
            self.env['mail.activity']._create_followups(followup_data)

        _logger.info(
            "Quick log: %s registered for %s by %s",
            activity_type.name, partner.name, self.env.user.name,
        )


class CommercialQuickLogLine(models.TransientModel):
    _name = 'commercial.quick.log.line'
    _description = 'Línea de Registro Rápido'

    wizard_id = fields.Many2one(
        'commercial.quick.log',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
    )
    activity_type_id = fields.Many2one(
        'mail.activity.type',
        string='Tipo',
        required=True,
        domain="[('category', '=', 'meeting'), ('res_model', '=', 'res.partner')]",
    )
    date = fields.Datetime(
        string='Fecha',
        default=fields.Datetime.now,
    )
    feedback = fields.Text(
        string='Notas',
    )
