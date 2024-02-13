# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError


class TransferEmployee(models.TransientModel):
    _name = 'hr.transfer.employee'
    _description = 'Transfer employee'

    employee_id = fields.Many2one('hr.employee', string="Collaborator",
                                  default=lambda self: self._context.get('active_id'), required=True)
    actual_department_id = fields.Many2one('hr.department', string='Actual department', readonly=True,
                                           related='employee_id.department_id')
    department_id = fields.Many2one('hr.department', string='Destination department', required=True)
    # Último día que trabajó en el departamento actual. El día siguiente a esta fecha es el inicio
    # de las actividades en el nuevo departamento.
    transfer_date = fields.Date('Transfer date', required=True, default=fields.Date.context_today,
                                help="Last day you worked in the current department. The day after this date is "
                                     "the start of activities in the new department.")

    def action_accept(self):
        if self.actual_department_id != self.department_id:
            edh = self.env['hr.employee.department.history'].search([
                ('employee_id', '=', self.employee_id.id), ('date_to', '=', False)
            ])
            if edh:
                if edh.date_from > self.transfer_date:
                    # La fecha de inicio tiene que ser menor o igual a la fecha de fin.
                    raise UserError(_('The start date has to be less than or equal to the end date.'))

                edh.date_to = self.transfer_date
                self.env['hr.employee.department.history'].create({
                    'employee_id': self.employee_id.id,
                    'department_id': self.department_id.id,
                    'date_from': self.transfer_date + relativedelta(days=1)
                })
                self.employee_id.department_id = self.department_id
            else:
                all_edh = self.env['hr.employee.department.history'].search([('employee_id', '=', self.employee_id.id)])
                if all_edh:
                    # Si existe historial de departamentos uno de ellos debe tener la fecha de fin vacía.
                    raise UserError(_('If there is a history of departments, one of them must have an empty end date.'))
                else:
                    self.env['hr.employee.department.history'].create({
                        'employee_id': self.employee_id.id,
                        'department_id': self.actual_department_id.id,
                        'date_from': self.employee_id.last_company_entry_date,
                        'date_to': self.transfer_date,
                    })
                    self.env['hr.employee.department.history'].create({
                        'employee_id': self.employee_id.id,
                        'department_id': self.department_id.id,
                        'date_from': self.transfer_date + relativedelta(days=1)
                    })
                    self.employee_id.department_id = self.department_id
        else:
            raise UserError(_('The destination department must be different from the current department.'))