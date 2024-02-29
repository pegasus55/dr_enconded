# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PrintVacationPlanningRequestAll(models.TransientModel):
    _name = 'hr.print.vacation.planning.request.all'
    _description = 'Print vacation planning request all'
    _inherit = 'hr.print.vacation.planning.request'
    
    def action_print_vpr(self):
        data = {
            'from': self.date_from,
            'to': self.date_to,
            'all': True
        }
        return self.env.ref('hr_dr_vacations.action_print_vacation_planning_request').report_action(self, data=data)