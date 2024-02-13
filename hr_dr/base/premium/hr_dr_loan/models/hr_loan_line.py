# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class LoanLine(models.Model):
    _name = "hr.loan.line"
    _description = "Loan detail"
    _inherit = ['mail.thread']
    _order = "loan_id, installment"
    _rec_name = 'employee_id'

    date = fields.Date(string="Payment date", required=True, readonly=True, tracking=True)
    installment = fields.Integer(string="Installment", required=True, readonly=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', string="Collaborator", required=True, readonly=True, tracking=True,
                                  ondelete='cascade')
    department_id = fields.Many2one('hr.department', string="Department", readonly=True, tracking=True)
    user_employee_requests_id = fields.Many2one('res.users', string="User requesting", related='employee_id.user_id',
                                                store=True)
    user_manager_department_employee_requests_id = fields.Many2one(
        'res.users', readonly=True, string="User manager department collaborator requesting")
    amount = fields.Monetary(string="Amount", currency_field='currency_id', required=True, readonly=True, tracking=True)
    paid = fields.Boolean(string="Paid", readonly=True, tracking=True)
    company_id = fields.Many2one('res.company', string="Company", related='loan_id.company_id', readonly=True)
    currency_id = fields.Many2one('res.currency', string="Currency", related='loan_id.currency_id', readonly=True)
    loan_id = fields.Many2one('hr.loan', string="Loan", readonly=True, ondelete='cascade')
    state = fields.Selection(related='loan_id.state', string='Status', store=True, readonly=True)