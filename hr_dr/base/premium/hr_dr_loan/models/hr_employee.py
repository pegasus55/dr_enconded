# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"
    
    def _compute_employee_loans(self):
        """This compute the loan amount and total loans count of an collaborator.
            """
        self.loan_count = self.env['hr.loan'].search_count([('employee_requests_id', '=', self.id),
                                                            ('state', 'in', ['approved', 'paid'])])
    loan_count = fields.Integer(string="Loan count", compute='_compute_employee_loans')