# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class CloneSalaryRule(models.TransientModel):
    _inherit = 'clone.salary.rule'

    def action_clone_salary_rule(self):
        for payroll_structure in self.payroll_structure_ids:
            for salary_rule in self.payroll_structure_id.rule_ids:
                self.env['hr.salary.rule'].sudo().create({
                    'name': salary_rule.name,
                    'category_id': salary_rule.category_id.id,
                    'code': salary_rule.code,
                    'sequence': salary_rule.sequence,
                    'struct_id': payroll_structure.id,
                    'active': salary_rule.active,
                    'appears_on_payslip': salary_rule.appears_on_payslip,
                    'appears_on_employee_cost_dashboard': salary_rule.appears_on_employee_cost_dashboard,
                    'appears_on_payroll_report': salary_rule.appears_on_payroll_report,
                    'condition_select': salary_rule.condition_select,
                    'condition_range': salary_rule.condition_range,
                    'condition_range_min': salary_rule.condition_range_min,
                    'condition_range_max': salary_rule.condition_range_max,
                    'condition_python': salary_rule.condition_python,
                    'amount_select': salary_rule.amount_select,
                    'amount_python_compute': salary_rule.amount_python_compute,
                    'amount_percentage_base': salary_rule.amount_percentage_base,
                    'quantity': salary_rule.quantity,
                    'amount_percentage': salary_rule.amount_percentage,
                    'amount_fix': salary_rule.amount_fix,
                    'note': salary_rule.note,
                })

    payroll_structure_id = fields.Many2one('hr.payroll.structure', string="Origin structure", required=True)
    payroll_structure_ids = fields.Many2many('hr.payroll.structure', string="Destination structures")

