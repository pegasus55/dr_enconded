# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class HrEmployee(models.Model):
    _inherit = "hr.employee"
    
    def _compute_employee_credit(self):
        self.credit_count = 0
        self.credit_count = self.env['hr.credit'].search_count([
            ('employee_requests_id', '=', self.id),
            ('state', '=', 'in_payroll')
        ])
    credit_count = fields.Integer(string="Credit count", compute='_compute_employee_credit')