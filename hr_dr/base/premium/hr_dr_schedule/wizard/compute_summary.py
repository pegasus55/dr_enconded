# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class ComputePeriodSummary(models.TransientModel):
    _name = "hr.compute.period.summary"
    _description = 'Compute period summary'

    def _default_period_id(self):
        last_period = self.env['hr.attendance.period'].search([
            ('end', '<=', datetime.utcnow().date()),
            ('state', 'in', ['open'])
        ], order='end desc', limit=1)
        if last_period:
            return last_period
        return False

    attendance_period_id = fields.Many2one('hr.attendance.period', string='Período de asistencia', required=True,
                                           default=_default_period_id)
    
    def action_compute_period_summary(self):
        summary_ids = self.env['hr.employee.period.summary'].sudo().search([
            ('attendance_period_id', '=', self.attendance_period_id.id),
        ])
        if summary_ids:
            summary_ids.unlink()

        employees = self.env['hr.employee'].sudo().search([
            ('active', '=', True),
            ('employee_admin', '=', False),
            ('state', 'in', ['affiliate', 'temporary', 'intern'])])

        for employee in employees:
            result_he = dict()
            employee_hour_extra = self.env['hr.employee.hour.extra'].sudo().search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'approved'),
                ('attendance_period_id', '=', self.attendance_period_id.id)
            ])
            for ehe in employee_hour_extra:
                key = "{}-{}".format(ehe.hour_extra_id.id, ehe.percentage_increase)
                if key in result_he:
                    result_he[key] = result_he.get(key, 0) + ehe.amount_approved
                else:
                    result_he[key] = ehe.amount_approved

            result_hn = dict()
            employee_hour_night = self.env['hr.employee.hour.night'].sudo().search([
                ('employee_id', '=', employee.id),
                ('attendance_period_id', '=', self.attendance_period_id.id)
            ])
            for ehn in employee_hour_night:
                key = "{}-{}".format(ehn.hour_night_id.id, ehn.percentage_increase)
                if key in result_hn:
                    result_hn[key] = result_hn.get(key, 0) + ehn.amount
                else:
                    result_hn[key] = ehn.amount

            eps = self.env['hr.employee.period.summary'].create({
                'attendance_period_id': self.attendance_period_id.id,
                'employee_id': employee.id,
                'department_employee_id': employee.department_id.id,
            })

            for k, v in result_he.items():
                self.env['hr.employee.period.summary.hour.extra'].create({
                    'period_summary_id': eps.id,
                    'hour_extra_id': int(k.split('-')[0]),
                    'percentage': float(k.split('-')[1]),
                    'amount': v,
                })

            for k, v in result_hn.items():
                self.env['hr.employee.period.summary.hour.night'].create({
                    'period_summary_id': eps.id,
                    'hour_night_id': int(k.split('-')[0]),
                    'percentage': float(k.split('-')[1]),
                    'amount': v,
                })

        tree_view_id = self.env.ref('hr_dr_schedule.hr_employee_period_summary_tree').id
        form_view_id = self.env.ref('hr_dr_schedule.hr_employee_period_summary_form').id
        search_view_id = self.env.ref('hr_dr_schedule.hr_employee_period_summary_search').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Resumen del período',
            'res_model': 'hr.employee.period.summary',
            'target': 'current',
            'view_mode': 'tree',
            'context': {'search_default_group_attendance_period_id': True,
                        'search_default_group_department_employee_id': 1},
            'search_view_id': [search_view_id, 'search'],
            'views': [(tree_view_id, 'tree'), (form_view_id, 'form')]
        }