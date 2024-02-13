# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AssignEmployeePlaceAttendance(models.TransientModel):
    _name = "assign.employee.place.attendance"
    _description = 'Assign collaborator place attendance'

    def action_assign_employee_place_attendance(self):
        if len(self.employee_ids) > 0:
            employees = self.employee_ids
        else:
            employees = self.env['hr.employee'].sudo().search(
                [('active', '=', True), ('state', 'in', ['affiliate', 'temporary', 'intern'])])

        for employee in employees:
            if self.delete_place_attendance_ids:
                employee.place_attendance_ids.unlink()

            for place in self.place_attendance_ids:
                employee.write({'place_attendance_ids': [(4, place.id, False)]})

    @api.onchange('department_ids')
    def _onchange_departments(self):
        self.employee_ids = self.env['hr.employee'].sudo().search(
            [('department_id', 'in', self.department_ids.ids)])

    @api.onchange('input_mode')
    def _onchange_input_mode(self):
        self.employee_ids = [(6, 0, [])]
        self.department_ids = [(6, 0, [])]

    _MODE = [
        ('employee', 'Employee'),
        ('department', 'Department')
    ]
    input_mode = fields.Selection(_MODE, string='Mode', default='employee', help='')
    department_ids = fields.Many2many('hr.department', string='Departments')
    employee_ids = fields.Many2many('hr.employee', string='Collaborator')
    place_attendance_ids = fields.Many2many('hr.place.attendance', string='Place attendance')
    delete_place_attendance_ids = fields.Boolean(string='Delete place attendance', default=True, help='')