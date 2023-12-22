# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class HrLoan(models.Model):
    _inherit = 'hr.loan'

    def create_inputs(self):
        payslip_input_type_id = self.env.ref('hr_dr_loan_payroll_enterprise.hr_payslip_input_type_PRESTAMOS')
        for rec in self:
            for line in rec.loan_lines:
                self.env['hr.input'].create({
                    'date': line.date,
                    'employee_id': line.employee_id.id,
                    'amount': line.amount,
                    'payslip_input_type_id': payslip_input_type_id.id,
                    'hr_loan_id': rec.id,
                    'hr_loan_line_id': line.id
                })

    def delete_inputs(self):
        for rec in self:
            for line in rec.loan_lines:
                self.env['hr.input'].search([
                    ("hr_loan_line_id", "=", line.id)
                ]).unlink()

    def mark_as_approved(self):
        self.create_inputs()
        super(HrLoan, self).mark_as_approved()

    def mark_as_approved_direct(self):
        self.create_inputs()
        super(HrLoan, self).mark_as_approved_direct()

    def cancel_request(self):
        self.delete_inputs()
        super(HrLoan, self).cancel_request()