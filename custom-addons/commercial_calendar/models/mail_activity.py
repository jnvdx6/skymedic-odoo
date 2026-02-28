import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    commercial_event_feedback = fields.Html(
        related='calendar_event_id.commercial_feedback',
        string='Feedback del Evento',
        readonly=True,
    )
    is_commercial_activity = fields.Boolean(
        string='Es Actividad Comercial',
        compute='_compute_is_commercial_activity',
        store=True,
    )

    @api.depends('activity_type_id', 'activity_type_id.category', 'activity_type_id.res_model')
    def _compute_is_commercial_activity(self):
        for activity in self:
            activity.is_commercial_activity = (
                activity.activity_type_id.category == 'meeting'
                and activity.activity_type_id.res_model == 'res.partner'
            )

    def _action_done(self, feedback=False, attachment_ids=None):
        """When marking a commercial activity as done:
        1. Sync feedback to calendar event
        2. Trigger follow-up rules
        """
        # Collect info before super() marks them done (may unlink)
        followup_data = []
        for activity in self:
            if not activity.is_commercial_activity:
                continue
            # Sync feedback
            if (feedback
                    and activity.calendar_event_id
                    and not activity.calendar_event_id.commercial_feedback):
                activity.calendar_event_id.commercial_feedback = feedback
            # Collect data for follow-up creation
            if activity.res_model == 'res.partner' and activity.res_id:
                followup_data.append({
                    'trigger_type_id': activity.activity_type_id.id,
                    'partner_id': activity.res_id,
                    'user_id': activity.user_id.id,
                })

        result = super()._action_done(feedback=feedback, attachment_ids=attachment_ids)

        # Create follow-up activities from rules
        self._create_followups(followup_data)

        return result

    def _create_followups(self, followup_data):
        """Create follow-up activities and events based on commercial.followup.rule."""
        if not followup_data:
            return
        FollowupRule = self.env['commercial.followup.rule']
        CalendarEvent = self.env['calendar.event']
        partner_model_id = self.env['ir.model']._get_id('res.partner')

        for data in followup_data:
            rules = FollowupRule.search([
                ('active', '=', True),
                ('trigger_activity_type_id', '=', data['trigger_type_id']),
            ], order='sequence')
            partner = self.env['res.partner'].browse(data['partner_id'])
            if not partner.exists():
                continue
            for rule in rules:
                deadline = fields.Date.today() + timedelta(days=rule.delay_days)
                summary = rule.summary_template or rule.followup_activity_type_id.name
                if '{partner}' in summary:
                    summary = summary.replace('{partner}', partner.name or '')

                # Create calendar event if configured
                event = False
                if rule.auto_create_event:
                    event = CalendarEvent.create({
                        'name': summary,
                        'start': fields.Datetime.to_string(
                            fields.Datetime.now() + timedelta(days=rule.delay_days)
                        ),
                        'stop': fields.Datetime.to_string(
                            fields.Datetime.now() + timedelta(days=rule.delay_days, hours=1)
                        ),
                        'commercial_activity_type_id': rule.followup_activity_type_id.id,
                        'commercial_partner_id': partner.id,
                        'user_id': data['user_id'],
                        'partner_ids': [(4, data['user_id'] and self.env['res.users'].browse(data['user_id']).partner_id.id),
                                        (4, partner.id)],
                        'description': rule.note_template or '',
                    })
                else:
                    # Create just a mail.activity without event
                    self.env['mail.activity'].create({
                        'activity_type_id': rule.followup_activity_type_id.id,
                        'summary': summary,
                        'note': rule.note_template or '',
                        'date_deadline': deadline,
                        'user_id': data['user_id'],
                        'res_model_id': partner_model_id,
                        'res_id': partner.id,
                    })

                _logger.info(
                    "Follow-up created: %s -> %s for %s in %d days",
                    rule.trigger_activity_type_id.name,
                    rule.followup_activity_type_id.name,
                    partner.name,
                    rule.delay_days,
                )
