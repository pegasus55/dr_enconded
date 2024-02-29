# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class DeleteEmployeeShift(models.TransientModel):
    _name = "delete.employee.shift"
    _description = 'Delete employee shift'
    
    def action_delete_employee_shift(self):
        if len(self.employee_ids) > 0:
            employees = self.employee_ids
        else:
            employees = self.env['hr.employee'].sudo().search([('active', '=', True),
                                                               ('employee_admin', '=', False),
                                                               ('state', 'in', ['affiliate', 'temporary', 'intern'])])

        dt_date_from = self.date_from + relativedelta(hour=0, minute=0, second=0)
        dt_date_to = self.date_to + relativedelta(hour=23, minute=59, second=59)
        employee_ids = [id for id in employees.ids]
        actual_employee_shift = self.env['hr.employee.shift'].sudo().search([
            ('employee_id', 'in', employee_ids),
            ('planned_start', '>=', dt_date_from),
            ('planned_start', '<=', dt_date_to)
        ])
        for aes in actual_employee_shift:
            aes.unlink()

        tree_view_id = self.env.ref('hr_dr_schedule.hr_employee_shift_tree').id
        form_view_id = self.env.ref('hr_dr_schedule.hr_employee_shift_form').id
        search_view_id = self.env.ref('hr_dr_schedule.hr_employee_shift_search').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Todos los turnos',
            'res_model': 'hr.employee.shift',
            'target': 'current',
            'view_mode': 'tree',
            'context': {'search_default_filter_last_period': True, 'search_default_group_department_employee_id': 1,
                        'search_default_group_employee_id': 1, 'search_default_group_year_planned_start': 1},
            'search_view_id': [search_view_id, 'search'],
            'views': [(tree_view_id, 'tree'), (form_view_id, 'form')]
        }

    @api.onchange('department_ids')
    def _onchange_departments(self):
        employees = self.env['hr.employee'].sudo().search([('department_id', 'in', self.department_ids.ids)])
        result = [e.id for e in employees]
        self.employee_ids = [(6, 0, result)]

    def _default_period_id(self):
        last_period = self.env['hr.attendance.period'].search([
            ('state', 'in', ['open'])
        ], order='end desc', limit=1)
        if last_period:
            return last_period
        return False

    @api.onchange('attendance_period_id')
    def _onchange_attendance_period_id(self):
        for rec in self:
            if rec.attendance_period_id:
                rec.date_from = rec.attendance_period_id.start
                rec.date_to = rec.attendance_period_id.end

    @api.onchange('input_mode')
    def _onchange_input_mode(self):
        self.employee_ids = [(6, 0, [])]
        self.department_ids = [(6, 0, [])]

    attendance_period_id = fields.Many2one('hr.attendance.period', string='Período de asistencia',
                                           default=_default_period_id)
    date_from = fields.Date('Desde', required=True)
    date_to = fields.Date('Hasta', required=True)
    _MODE = [
        ('employee', 'Colaborador'),
        ('department', 'Departamento')
    ]
    input_mode = fields.Selection(_MODE, string='Modo', default='employee', help='')
    department_ids = fields.Many2many('hr.department', string='Departamentos')
    employee_ids = fields.Many2many('hr.employee', string='Colaboradores')