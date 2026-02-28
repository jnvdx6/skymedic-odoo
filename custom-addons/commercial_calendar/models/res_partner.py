import logging
from datetime import timedelta

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

# Score mappings
VOLUME_SCORE = {
    'Platinum': 25, 'Gold': 20, 'Silver': 15, 'Bronze': 10, 'Starter': 5,
}
TREND_SCORE = {
    'growth': 20, 'new': 18, 'recovered': 15, 'stable': 12, 'decline': 5, 'inactive': 0,
}
ACTIVITY_RECENCY_SCORE = [
    (3, 20), (6, 15), (12, 10), (24, 5),
]
FREQUENCY_SCORE = {
    'Recurrente': 15, 'Regular': 10, 'Ocasional': 5, 'Compra única': 2,
}
VISIT_FRESHNESS = [
    (30, 10), (60, 7), (90, 4),
]


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # --- Existing fields ---
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

    # --- New v2 fields ---
    commercial_user_id = fields.Many2one(
        'res.users',
        string='Comercial Asignado',
        tracking=True,
        index=True,
    )
    commercial_score = fields.Float(
        string='Puntuación Comercial',
        default=0,
    )
    days_since_last_visit = fields.Integer(
        string='Días sin visita',
        default=0,
    )
    visit_frequency_target = fields.Integer(
        string='Objetivo visitas/año',
        default=0,
    )
    visit_count_ytd = fields.Integer(
        string='Visitas este año',
        default=0,
    )
    commercial_alert_overdue = fields.Boolean(
        string='Alerta: sin visitar',
        default=False,
    )
    commercial_alert_declining = fields.Boolean(
        string='Alerta: en declive',
        default=False,
    )
    commercial_alert_opportunity = fields.Boolean(
        string='Alerta: oportunidad',
        default=False,
    )

    # -------------------------------------------------------------------------
    # Existing computes
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------
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

    def action_quick_log_visit(self):
        """Open quick log wizard pre-set to Visita type."""
        self.ensure_one()
        visita_type = self.env.ref(
            'commercial_calendar.activity_type_visita', raise_if_not_found=False
        )
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'commercial.quick.log',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_activity_type_id': visita_type.id if visita_type else False,
            },
        }

    def action_quick_log_call(self):
        """Open quick log wizard pre-set to Llamada type."""
        self.ensure_one()
        llamada_type = self.env.ref(
            'commercial_calendar.activity_type_llamada', raise_if_not_found=False
        )
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'commercial.quick.log',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_activity_type_id': llamada_type.id if llamada_type else False,
            },
        }

    # -------------------------------------------------------------------------
    # Score computation
    # -------------------------------------------------------------------------
    def _compute_single_score(self):
        """Compute commercial_score for a single partner. Returns the score."""
        self.ensure_one()
        score = 0.0
        today = fields.Date.today()

        # 1) Volume (25pts) — from volume_tag_ids
        if hasattr(self, 'volume_tag_ids') and self.volume_tag_ids:
            tag_name = self.volume_tag_ids[0].name
            score += VOLUME_SCORE.get(tag_name, 0)

        # 2) Trend (20pts) — from trend_tag_ids
        if hasattr(self, 'trend_tag_ids') and self.trend_tag_ids:
            trend_type = self.trend_tag_ids[0].trend_type
            score += TREND_SCORE.get(trend_type, 0)

        # 3) Purchase recency (20pts) — from activity_tag_ids (months since last sale)
        if hasattr(self, 'activity_tag_ids') and self.activity_tag_ids:
            tag = self.activity_tag_ids[0]
            months_from = tag.months_from
            recency_pts = 0
            for threshold_months, pts in ACTIVITY_RECENCY_SCORE:
                if months_from <= threshold_months:
                    recency_pts = pts
                    break
            score += recency_pts

        # 4) Frequency (15pts) — from frequency_tag_ids
        if hasattr(self, 'frequency_tag_ids') and self.frequency_tag_ids:
            tag_name = self.frequency_tag_ids[0].name
            score += FREQUENCY_SCORE.get(tag_name, 0)

        # 5) Cross-sell opportunity (10pts) — from crosssell_tag_ids
        if hasattr(self, 'crosssell_tag_ids') and self.crosssell_tag_ids:
            # Each cross-sell tag gives points, max 10
            pts = min(len(self.crosssell_tag_ids) * 5, 10)
            score += pts

        # 6) Visit freshness (10pts) — based on days_since_last_visit
        if self.days_since_last_visit == 0 and self.last_commercial_activity_date:
            # Visited today or very recently
            score += 10
        elif self.days_since_last_visit > 0:
            freshness_pts = 0
            for threshold_days, pts in VISIT_FRESHNESS:
                if self.days_since_last_visit <= threshold_days:
                    freshness_pts = pts
                    break
            score += freshness_pts

        return score

    def _recompute_commercial_data(self):
        """Recompute all commercial stored fields for self."""
        today = fields.Date.today()
        year_start = today.replace(month=1, day=1)
        visita_type = self.env.ref(
            'commercial_calendar.activity_type_visita', raise_if_not_found=False
        )

        for partner in self:
            # days_since_last_visit
            if partner.last_commercial_activity_date:
                partner.days_since_last_visit = (today - partner.last_commercial_activity_date).days
            else:
                partner.days_since_last_visit = 9999

            # visit_count_ytd — count done visits this year
            ytd_count = 0
            if visita_type:
                ytd_count = self.env['calendar.event'].search_count([
                    ('commercial_partner_id', '=', partner.id),
                    ('commercial_activity_type_id', '=', visita_type.id),
                    ('commercial_status', '=', 'done'),
                    ('start', '>=', fields.Datetime.to_string(
                        fields.Datetime.now().replace(
                            month=1, day=1, hour=0, minute=0, second=0
                        )
                    )),
                ])
            partner.visit_count_ytd = ytd_count

            # Alerts
            partner.commercial_alert_overdue = partner.days_since_last_visit > 60
            partner.commercial_alert_declining = (
                hasattr(partner, 'trend_tag_ids')
                and partner.trend_tag_ids
                and partner.trend_tag_ids[0].trend_type in ('decline', 'inactive')
            )
            partner.commercial_alert_opportunity = (
                hasattr(partner, 'crosssell_tag_ids')
                and bool(partner.crosssell_tag_ids)
            )

            # Score
            partner.commercial_score = partner._compute_single_score()

    # -------------------------------------------------------------------------
    # Crons
    # -------------------------------------------------------------------------
    @api.model
    def _cron_recompute_commercial_scores(self):
        """Daily cron: recompute commercial scores for all partners with a commercial_user_id."""
        partners = self.search([('commercial_user_id', '!=', False)])
        batch_size = 100
        for i in range(0, len(partners), batch_size):
            batch = partners[i:i + batch_size]
            batch._recompute_commercial_data()
            self.env.cr.commit()
        _logger.info("Commercial scores recomputed for %d partners", len(partners))

    @api.model
    def _cron_notify_unvisited_clients(self):
        """Weekly cron: notify commercial users about unvisited clients with targets."""
        partners = self.search([
            ('commercial_user_id', '!=', False),
            ('visit_frequency_target', '>', 0),
            ('commercial_alert_overdue', '=', True),
        ])
        # Group by commercial user
        by_user = {}
        for p in partners:
            by_user.setdefault(p.commercial_user_id, self.env['res.partner'])
            by_user[p.commercial_user_id] |= p
        for user, user_partners in by_user.items():
            names = ', '.join(user_partners[:10].mapped('name'))
            extra = len(user_partners) - 10
            if extra > 0:
                names += _(" y %d más", extra)
            body = _(
                "Tienes <b>%(count)d clientes</b> sin visitar recientemente: %(names)s",
                count=len(user_partners),
                names=names,
            )
            user.partner_id.message_post(
                body=body,
                message_type='notification',
                subtype_xmlid='mail.mt_note',
                partner_ids=user.partner_id.ids,
            )
        _logger.info("Unvisited client notifications sent to %d users", len(by_user))
