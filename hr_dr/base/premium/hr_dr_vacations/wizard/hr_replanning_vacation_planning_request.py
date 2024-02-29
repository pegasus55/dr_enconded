# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ReplanningVacationPlanningRequest(models.TransientModel):
    _name = 'hr.replanning.vacation.planning.request'
    _description = 'Re-planning vacation planning request'

    # Planificación Actual.
    actual_vacation_planning_request_id = fields.Many2one('hr.vacation.planning.request',
                                                          string='Actual vacation planning request', readonly=True,
                                                          default=lambda self: self._context.get('active_id'))
    employee_requests_id = fields.Many2one('hr.employee', string="Collaborator", readonly=True,
                                           related='actual_vacation_planning_request_id.employee_requests_id')
    department_employee_requests_id = fields.Many2one('hr.department', string="Department employee requesting",
                                                      related='actual_vacation_planning_request_id.department_employee_requests_id',
                                                      readonly=True)
    date_from = fields.Date('From', readonly=True, related='actual_vacation_planning_request_id.date_from')
    date_to = fields.Date('To', readonly=True, related='actual_vacation_planning_request_id.date_to')
    date_incorporation = fields.Date('Incorporation date', readonly=True,
                                     related='actual_vacation_planning_request_id.date_incorporation')
    number_of_days = fields.Integer(string="Number of days planned", readonly=True,
                                    related='actual_vacation_planning_request_id.number_of_days')

    # Replanificación.
    commentary_new = fields.Text(string="Commentary", required=True)
    date_from_new = fields.Date('From', required=True)
    date_to_new = fields.Date('To', required=True)
    
    def action_replanning(self):

        vpr_new = self.env['hr.vacation.planning.request'].create({
            'employee_requests_id': self.employee_requests_id.id,
            'parent_id': self.actual_vacation_planning_request_id.id,
            'state': 'draft',
            'commentary': self.commentary_new,
            'date_to': self.date_to_new,
            'date_from': self.date_from_new
        })

        if vpr_new:
            vpr_new.confirm_request()
            self.actual_vacation_planning_request_id.state = 'replanned'
    
    def action_replanning_direct(self):

        vpr_new = self.env['hr.vacation.planning.request'].create({
            'employee_requests_id': self.employee_requests_id.id,
            'parent_id': self.actual_vacation_planning_request_id.id,
            'state': 'approved',
            'commentary': self.commentary_new,
            'date_to': self.date_to_new,
            'date_from': self.date_from_new
        })

        if vpr_new:
            vpr_new.confirm_vacation_planning_request_direct()
            self.actual_vacation_planning_request_id.state = 'replanned'