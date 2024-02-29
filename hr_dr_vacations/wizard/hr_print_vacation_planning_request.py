# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime


class PrintVacationPlanningRequest(models.TransientModel):
    _name = 'hr.print.vacation.planning.request'
    _description = 'Print vacation planning request'

    def _default_date_from(self):
        default_date_from = '%s-01-01' % datetime.now().year
        return datetime.strptime(str(default_date_from), '%Y-%m-%d').date()

    date_from = fields.Date('From', required=True, default=_default_date_from)
    date_to = fields.Date('To', required=True, compute='_date_to')

    @api.depends('date_from')
    def _date_to(self):
        default_date_to = '%s-12-31' % self.date_from.year
        self.date_to = datetime.strptime(str(default_date_to), '%Y-%m-%d').date()
    
    def action_print_vpr(self):
        data = {
            'from': self.date_from,
            'to': self.date_to,
            'all': False
        }
        return self.env.ref('hr_dr_vacations.action_print_vacation_planning_request').report_action(self, data=data)