from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    commercial_event_ids = fields.One2many(
        'calendar.event',
        'commercial_partner_id',
        string='Eventos Comerciales',
    )
    commercial_event_count = fields.Integer(
        string='Nº Eventos Comerciales',
        compute='_compute_commercial_event_count',
    )
    next_commercial_activity_date = fields.Date(
        string='Próxima Actividad Comercial',
        compute='_compute_next_commercial_activity',
        store=True,
    )
    next_commercial_activity_type = fields.Char(
        string='Tipo Próxima Actividad',
        compute='_compute_next_commercial_activity',
        store=True,
    )
    last_commercial_activity_date = fields.Date(
        string='Última Actividad Comercial',
        compute='_compute_last_commercial_activity',
        store=True,
    )
    commercial_activity_summary = fields.Text(
        string='Resumen Actividad Comercial',
        compute='_compute_commercial_activity_summary',
    )

    def _compute_commercial_event_count(self):
        for partner in self:
            partner.commercial_event_count = len(partner.commercial_event_ids)

    @api.depends('activity_ids.date_deadline', 'activity_ids.activity_type_id')
    def _compute_next_commercial_activity(self):
        commercial_types = self.env['mail.activity.type'].search([
            ('category', '=', 'meeting'),
            ('res_model', '=', 'res.partner'),
        ])
        for partner in self:
            if not commercial_types:
                partner.next_commercial_activity_date = False
                partner.next_commercial_activity_type = False
                continue
            activities = self.env['mail.activity'].search([
                ('res_model', '=', 'res.partner'),
                ('res_id', '=', partner.id),
                ('activity_type_id', 'in', commercial_types.ids),
            ], order='date_deadline asc', limit=1)
            partner.next_commercial_activity_date = activities.date_deadline if activities else False
            partner.next_commercial_activity_type = activities.activity_type_id.name if activities else False

    @api.depends('commercial_event_ids.start', 'commercial_event_ids.commercial_status')
    def _compute_last_commercial_activity(self):
        for partner in self:
            done_events = partner.commercial_event_ids.filtered(
                lambda e: e.commercial_status == 'done'
            ).sorted('start', reverse=True)
            partner.last_commercial_activity_date = done_events[0].start.date() if done_events else False

    def _compute_commercial_activity_summary(self):
        for partner in self:
            parts = []
            if partner.next_commercial_activity_date:
                parts.append(_("Próxima: %s (%s)", partner.next_commercial_activity_type or '', partner.next_commercial_activity_date))
            if partner.last_commercial_activity_date:
                parts.append(_("Última: %s", partner.last_commercial_activity_date))
            parts.append(_("Eventos: %d", partner.commercial_event_count))
            partner.commercial_activity_summary = ' | '.join(parts) if parts else False

    def action_view_commercial_events(self):
        """Open calendar filtered for this partner's commercial events."""
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("calendar.action_calendar_event")
        action['domain'] = [('commercial_partner_id', '=', self.id)]
        action['context'] = {
            'default_commercial_partner_id': self.id,
            'default_partner_ids': [(4, self.id)],
        }
        return action

    def action_schedule_commercial_activity(self):
        """Open calendar event form pre-filled for commercial activity."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'calendar.event',
            'views': [(False, 'form')],
            'context': {
                'default_commercial_partner_id': self.id,
                'default_partner_ids': [(4, self.env.user.partner_id.id), (4, self.id)],
                'default_name': _('Actividad Comercial - %s', self.name),
            },
            'target': 'current',
        }
