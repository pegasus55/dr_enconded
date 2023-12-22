# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError


class HrDepartureWizard(models.TransientModel):
    _inherit = 'hr.departure.wizard'

    @api.onchange('departure_reason_id')
    def onchange_departure_reason_id(self):
        if self.code == 'FIR':
            department_unemployed = self.env.ref('hr_dr_employee.department_unemployed', False)
            self.department_id = department_unemployed
        elif self.code == 'RES':
            department_unemployed = self.env.ref('hr_dr_employee.department_unemployed', False)
            self.department_id = department_unemployed
        elif self.code == 'RET':
            department_retired = self.env.ref('hr_dr_employee.department_retired', False)
            self.department_id = department_retired

    @api.depends('last_company_entry_date')
    def _compute_time_worked(self):
        for eec in self:
            if eec.last_company_entry_date:
                to = self.departure_date + relativedelta(days=1)
                rd = relativedelta(to, eec.last_company_entry_date)
                eec.time_worked = _("{} year(s) {} month(s) {} day(s)").format(rd.years, rd.months, rd.days)
            else:
                eec.time_worked = _("{} year(s) {} month(s) {} day(s)").format('-', '-', '-')

    code = fields.Char(string="Code", related='departure_reason_id.code')
    department_id = fields.Many2one('hr.department', string='Destination department')
    time_worked = fields.Char(string="Time worked", compute=_compute_time_worked)
    actual_department_id = fields.Many2one('hr.department', string='Actual department', readonly=True,
                                           related='employee_id.department_id')
    last_company_entry_date = fields.Date('Date of entry', readonly=True,
                                          related='employee_id.last_company_entry_date')
    archive_user = fields.Boolean('Archive user', default=True)
    end_current_contract = fields.Boolean('End current contract', default=True)
    pension = fields.Float(string='Pension', digits='Employee')
    retirement_certificate = fields.Binary("Retirement certificate", attachment=True, help="")

    def action_register_departure(self):
        super(HrDepartureWizard, self).action_register_departure()

        if self.departure_reason_id.code == "RET":
            if self.pension == 0:
                raise UserError(_('The pension must be different from 0.'))

        if self.actual_department_id != self.department_id:
            edh = self.env['hr.employee.department.history'].search([
                ('employee_id', '=', self.employee_id.id), ('date_to', '=', False)
            ])
            if edh:
                edh.date_to = self.departure_date
                self.env['hr.employee.department.history'].create({
                    'employee_id': self.employee_id.id,
                    'department_id': self.department_id.id,
                    'date_from': self.departure_date + relativedelta(days=1)
                })
            else:
                all_edh = self.env['hr.employee.department.history'].search([
                    ('employee_id', '=', self.employee_id.id)])
                if all_edh:
                    raise UserError(_('If there is a history of departments, one of them must have an empty end date.'))
                else:
                    self.env['hr.employee.department.history'].create({
                        'employee_id': self.employee_id.id,
                        'department_id': self.actual_department_id.id,
                        'date_to': self.departure_date,
                        'date_from': self.employee_id.last_company_entry_date
                    })
                    self.env['hr.employee.department.history'].create({
                        'employee_id': self.employee_id.id,
                        'department_id': self.department_id.id,
                        'date_from': self.departure_date + relativedelta(days=1)
                    })

            ech = self.env['hr.employee.company.history'].search([
                ('employee_id', '=', self.employee_id.id), ('date_to', '=', False)
            ])
            if ech:
                ech.date_to = self.departure_date
            else:
                all_ech = self.env['hr.employee.company.history'].search([
                    ('employee_id', '=', self.employee_id.id)])
                if all_ech:
                    raise UserError(_('If there is a history in the company, one of them must have an empty end date.'))
                else:
                    self.env['hr.employee.company.history'].create({
                        'employee_id': self.employee_id.id,
                        'date_to': self.departure_date,
                        'date_from': self.employee_id.last_company_entry_date
                    })

            unemployed_type = ''
            if self.code == 'FIR':
                unemployed_type = 'fired'
            elif self.code == 'RES':
                unemployed_type = 'resigned'

            if self.code == 'RET':
                self.employee_id.state = 'retired'
                self.employee_id.retirement_certificate = self.retirement_certificate
                self.employee_id.pension = self.pension
                if 'hr_dr_employee_notifications' in self.env.registry._init_modules:
                    self.employee_id.action_notify_personal_retired()
            elif self.code in ['FIR', 'RES']:
                self.employee_id.state = 'unemployed'
                if 'hr_dr_employee_notifications' in self.env.registry._init_modules:
                    self.employee_id.action_notify_personal_exit()

            self.employee_id.unemployed_type = unemployed_type
            self.employee_id.department_id = self.department_id

            if self.archive_user:
                user = self.employee_id.user_id
                user.toggle_active()

            # if self.end_current_contract:
            #     self.employee_id.contract_id.date_end = self.departure_date
        else:
            raise UserError(_('The destination department must be different from the current department.'))


