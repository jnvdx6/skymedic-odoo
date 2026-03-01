import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

# Mapping from activity type name to calendar event type xmlid
ACTIVITY_TO_EVENT_TYPE = {
    'Visita Comercial': 'commercial_calendar.event_type_visita',
    'Demo': 'commercial_calendar.event_type_demo',
    'Formación': 'commercial_calendar.event_type_formacion',
    'Llamada Comercial': 'commercial_calendar.event_type_llamada',
    'Seguimiento': 'commercial_calendar.event_type_seguimiento',
    'Presentación': 'commercial_calendar.event_type_presentacion',
}


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    commercial_activity_type_id = fields.Many2one(
        'mail.activity.type',
        string='Tipo Actividad Comercial',
        domain="[('category', '=', 'meeting'), ('res_model', '=', 'res.partner')]",
        tracking=True,
        help="Tipo de actividad comercial asociada a este evento.",
    )
    commercial_partner_id = fields.Many2one(
        'res.partner',
        string='Contacto Comercial',
        index=True,
        tracking=True,
        help="Contacto principal vinculado a esta actividad comercial.",
    )
    commercial_feedback = fields.Html(
        string='Feedback Comercial',
        help="Notas y feedback de la actividad comercial.",
    )
    commercial_status = fields.Selection(
        [
            ('planned', 'Planificada'),
            ('today', 'Hoy'),
            ('overdue', 'Vencida'),
            ('done', 'Realizada'),
        ],
        string='Estado Comercial',
        compute='_compute_commercial_status',
        store=True,
    )
    is_commercial = fields.Boolean(
        string='Es Comercial',
        compute='_compute_is_commercial',
        store=True,
        index=True,
    )
    overdue_notified = fields.Boolean(
        string='Notificación Vencida Enviada',
        default=False,
        help="Control interno para evitar notificaciones duplicadas.",
    )

    @api.depends('commercial_activity_type_id')
    def _compute_is_commercial(self):
        for event in self:
            event.is_commercial = bool(event.commercial_activity_type_id)

    @api.depends('activity_ids', 'activity_ids.date_deadline', 'start', 'commercial_activity_type_id')
    def _compute_commercial_status(self):
        today = fields.Date.today()
        for event in self:
            if not event.is_commercial:
                event.commercial_status = False
                continue
            # Check linked activities (active ones)
            active_activities = event.activity_ids
            if not active_activities:
                # No active activities - check event date to determine status
                event_date = event.start.date() if event.start else False
                if not event_date:
                    event.commercial_status = 'done'
                elif event_date < today:
                    event.commercial_status = 'done'
                elif event_date == today:
                    event.commercial_status = 'today'
                else:
                    event.commercial_status = 'planned'
                continue
            # Use earliest deadline from active activities
            deadlines = active_activities.mapped('date_deadline')
            if not deadlines:
                event.commercial_status = 'planned'
                continue
            earliest = min(deadlines)
            if earliest < today:
                event.commercial_status = 'overdue'
            elif earliest == today:
                event.commercial_status = 'today'
            else:
                event.commercial_status = 'planned'

    @api.onchange('commercial_activity_type_id')
    def _onchange_commercial_activity_type_id(self):
        """Auto-set calendar event type tag when commercial type is selected."""
        if not self.commercial_activity_type_id:
            return
        type_name = self.commercial_activity_type_id.name
        xmlid = ACTIVITY_TO_EVENT_TYPE.get(type_name)
        if xmlid:
            event_type = self.env.ref(xmlid, raise_if_not_found=False)
            if event_type and event_type not in self.categ_ids:
                self.categ_ids = [(4, event_type.id)]

    @api.onchange('commercial_partner_id')
    def _onchange_commercial_partner_id(self):
        """Add commercial partner as attendee."""
        if self.commercial_partner_id and self.commercial_partner_id not in self.partner_ids:
            self.partner_ids = [(4, self.commercial_partner_id.id)]

    @api.model_create_multi
    def create(self, vals_list):
        events = super().create(vals_list)
        for event in events:
            if event.commercial_activity_type_id and event.commercial_partner_id:
                # Check if an activity was already created on this partner by the base create
                partner_model_id = self.env['ir.model']._get_id('res.partner')
                existing = event.activity_ids.filtered(
                    lambda a: a.res_model_id.id == partner_model_id
                    and a.res_id == event.commercial_partner_id.id
                )
                if not existing:
                    self.env['mail.activity'].create({
                        'activity_type_id': event.commercial_activity_type_id.id,
                        'summary': event.name,
                        'note': event.description or '',
                        'date_deadline': event.start.date() if event.start else fields.Date.today(),
                        'user_id': event.user_id.id,
                        'res_model_id': partner_model_id,
                        'res_id': event.commercial_partner_id.id,
                        'calendar_event_id': event.id,
                    })
        return events

    def write(self, vals):
        res = super().write(vals)
        if 'commercial_feedback' in vals and vals['commercial_feedback']:
            for event in self:
                if event.activity_ids and event.commercial_feedback:
                    for activity in event.activity_ids:
                        if not activity.note or activity.note == '<p><br></p>':
                            activity.note = event.commercial_feedback
        return res

    @api.model
    def _cron_notify_overdue_commercial(self):
        """Cron job: notify responsible users about overdue commercial events."""
        overdue_events = self.search([
            ('is_commercial', '=', True),
            ('commercial_status', '=', 'overdue'),
            ('overdue_notified', '=', False),
        ])
        for event in overdue_events:
            if not event.user_id:
                continue
            type_name = event.commercial_activity_type_id.name or 'Actividad'
            partner_name = event.commercial_partner_id.name or 'Sin contacto'
            event_date = event.start.date() if event.start else ''
            body = _(
                "Tienes una <b>%(type)s</b> vencida con <b>%(partner)s</b> "
                "programada para el %(date)s que aún no se ha completado.",
                type=type_name,
                partner=partner_name,
                date=event_date,
            )
            event.message_post(
                body=body,
                message_type='notification',
                subtype_xmlid='mail.mt_note',
                partner_ids=event.user_id.partner_id.ids,
            )
            event.overdue_notified = True
            _logger.info(
                "Notificación de evento comercial vencido enviada: %s -> %s",
                event.name, event.user_id.name,
            )
