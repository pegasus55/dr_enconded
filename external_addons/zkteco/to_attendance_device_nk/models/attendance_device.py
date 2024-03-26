from odoo import models, fields, api, registry, _


class AttendanceDevice(models.Model):
    _inherit = 'attendance.device'

    @api.depends('device_user_ids',
                 'device_user_ids.active',
                 'device_user_ids.employee_id',
                 'device_user_ids.employee_id.active',
                 'company_id')
    def _compute_employees(self):
        HrEmployee = self.env['hr.employee']
        for r in self:
            if r.company_id:
                r.update({
                    'unmapped_employee_ids': [(6, 0, HrEmployee.search([('company_id', '=', r.company_id.id), ('id', 'not in', r.device_user_ids.mapped('employee_id').ids)]).ids)],
                    'mapped_employee_ids': [(6, 0, r.device_user_ids.mapped('employee_id').filtered(lambda employee: employee.active is True).ids)],
                    })
            else:
                r.update({
                    'unmapped_employee_ids': [(6, 0, HrEmployee.search([('id', 'not in', r.device_user_ids.mapped('employee_id').ids)]).ids)],
                    'mapped_employee_ids': [(6, 0, r.device_user_ids.mapped('employee_id').filtered(lambda employee: employee.active is True).ids)],
                })