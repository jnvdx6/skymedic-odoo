from odoo import api, fields, models


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
        """When marking a commercial activity as done, also update the
        calendar event's commercial_feedback field."""
        if feedback:
            for activity in self:
                if (activity.is_commercial_activity
                        and activity.calendar_event_id
                        and not activity.calendar_event_id.commercial_feedback):
                    activity.calendar_event_id.commercial_feedback = feedback
        return super()._action_done(feedback=feedback, attachment_ids=attachment_ids)
