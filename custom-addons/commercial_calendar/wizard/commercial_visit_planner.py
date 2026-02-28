import logging
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CommercialVisitPlanner(models.TransientModel):
    _name = 'commercial.visit.planner'
    _description = 'Planificador Inteligente de Visitas'

    commercial_user_id = fields.Many2one(
        'res.users',
        string='Comercial',
        default=lambda self: self.env.user,
    )
    min_score = fields.Float(
        string='Puntuación mínima',
        default=0,
    )
    only_overdue = fields.Boolean(
        string='Solo vencidas',
        default=False,
    )
    only_declining = fields.Boolean(
        string='Solo en declive',
        default=False,
    )
    only_opportunity = fields.Boolean(
        string='Solo con oportunidad',
        default=False,
    )
    max_results = fields.Integer(
        string='Máximo resultados',
        default=20,
    )
    line_ids = fields.One2many(
        'commercial.visit.planner.line',
        'wizard_id',
        string='Clientes Sugeridos',
    )

    def action_search(self):
        """Search and prioritize clients for visits."""
        self.ensure_one()
        domain = [
            ('commercial_user_id', '=', self.commercial_user_id.id),
            ('is_company', '=', True),
        ]
        if self.min_score > 0:
            domain.append(('commercial_score', '>=', self.min_score))
        if self.only_overdue:
            domain.append(('commercial_alert_overdue', '=', True))
        if self.only_declining:
            domain.append(('commercial_alert_declining', '=', True))
        if self.only_opportunity:
            domain.append(('commercial_alert_opportunity', '=', True))

        partners = self.env['res.partner'].search(domain, limit=200)

        # Compute priority scores
        scored = []
        for partner in partners:
            priority = self._compute_priority(partner)
            reason = self._get_priority_reason(partner)
            scored.append((priority, partner, reason))

        scored.sort(key=lambda x: x[0], reverse=True)
        scored = scored[:self.max_results]

        # Clear existing lines and create new ones
        self.line_ids.unlink()
        lines = []
        for priority, partner, reason in scored:
            lines.append((0, 0, {
                'partner_id': partner.id,
                'priority_score': priority,
                'reason': reason,
                'commercial_score': partner.commercial_score,
                'days_since_visit': partner.days_since_last_visit,
                'selected': priority >= 50,  # Auto-select high priority
            }))
        self.write({'line_ids': lines})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'commercial.visit.planner',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    def _compute_priority(self, partner):
        """Compute visit priority score (0-100)."""
        priority = 0
        days = partner.days_since_last_visit

        # Time since last visit (max 30pts)
        if days > 180:
            priority += 30
        elif days > 90:
            priority += 25
        elif days > 60:
            priority += 15
        elif days > 30:
            priority += 10

        # Client value / tier (max 25pts)
        if hasattr(partner, 'volume_tag_ids') and partner.volume_tag_ids:
            tier_name = partner.volume_tag_ids[0].name
            tier_scores = {
                'Platinum': 25, 'Gold': 20, 'Silver': 15, 'Bronze': 10, 'Starter': 5,
            }
            priority += tier_scores.get(tier_name, 0)

        # Declining / inactive (max 20pts)
        if hasattr(partner, 'trend_tag_ids') and partner.trend_tag_ids:
            trend_type = partner.trend_tag_ids[0].trend_type
            if trend_type == 'decline':
                priority += 20
            elif trend_type == 'inactive':
                priority += 15

        # Cross-sell opportunity (max 15pts)
        if partner.commercial_alert_opportunity:
            priority += 15

        # Degraded recency (max 10pts)
        if hasattr(partner, 'activity_tag_ids') and partner.activity_tag_ids:
            months_from = partner.activity_tag_ids[0].months_from
            if months_from >= 6:
                priority += 10
            elif months_from >= 3:
                priority += 5

        return min(priority, 100)

    def _get_priority_reason(self, partner):
        """Generate a human-readable reason for visit priority."""
        reasons = []
        days = partner.days_since_last_visit
        if days > 180:
            reasons.append(_("Sin visita > 6 meses"))
        elif days > 90:
            reasons.append(_("Sin visita > 3 meses"))
        elif days > 60:
            reasons.append(_("Sin visita > 2 meses"))

        if partner.commercial_alert_declining:
            reasons.append(_("Tendencia en declive"))
        if partner.commercial_alert_opportunity:
            reasons.append(_("Oportunidad cross-sell"))

        if hasattr(partner, 'volume_tag_ids') and partner.volume_tag_ids:
            tier = partner.volume_tag_ids[0].name
            if tier in ('Platinum', 'Gold'):
                reasons.append(_("Cliente %s", tier))

        return ', '.join(reasons) if reasons else _("Seguimiento regular")

    def action_schedule_selected(self):
        """Create calendar events for selected partners."""
        self.ensure_one()
        selected = self.line_ids.filtered('selected')
        if not selected:
            raise UserError(_("Selecciona al menos un cliente."))

        visita_type = self.env.ref(
            'commercial_calendar.activity_type_visita', raise_if_not_found=False
        )
        if not visita_type:
            raise UserError(_("No se encontró el tipo de actividad 'Visita Comercial'."))

        # Create events starting from tomorrow
        base_date = fields.Datetime.now() + timedelta(days=1)
        events_created = 0
        for idx, line in enumerate(selected):
            event_start = base_date + timedelta(days=idx)
            self.env['calendar.event'].create({
                'name': _('Visita Comercial - %s', line.partner_id.name),
                'start': event_start,
                'stop': event_start + timedelta(hours=1),
                'commercial_activity_type_id': visita_type.id,
                'commercial_partner_id': line.partner_id.id,
                'user_id': self.commercial_user_id.id,
                'partner_ids': [
                    (4, self.commercial_user_id.partner_id.id),
                    (4, line.partner_id.id),
                ],
            })
            events_created += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Visitas Programadas"),
                'message': _("%d visitas programadas correctamente.", events_created),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }


class CommercialVisitPlannerLine(models.TransientModel):
    _name = 'commercial.visit.planner.line'
    _description = 'Línea del Planificador de Visitas'
    _order = 'priority_score desc'

    wizard_id = fields.Many2one(
        'commercial.visit.planner',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    selected = fields.Boolean(
        string='Sel.',
        default=False,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        readonly=True,
    )
    priority_score = fields.Float(
        string='Prioridad',
        readonly=True,
    )
    reason = fields.Char(
        string='Motivo',
        readonly=True,
    )
    commercial_score = fields.Float(
        string='Score',
        readonly=True,
    )
    days_since_visit = fields.Integer(
        string='Días',
        readonly=True,
    )
