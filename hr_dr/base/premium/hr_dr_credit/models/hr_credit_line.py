# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class CreditLine(models.Model):
    _name = "hr.credit.line"
    _description = "Credit detail"
    _inherit = ['mail.thread']
    _order = "credit_id, installment"
    _rec_name = 'employee_id'

    date = fields.Date(string="Payment date", required=True, readonly=True, tracking=True)
    installment = fields.Integer(string="Installment", required=True, readonly=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', string="Collaborator", required=True, readonly=True,
                                  tracking=True, ondelete='cascade')
    department_id = fields.Many2one('hr.department', string="Department", readonly=True, tracking=True)
    user_employee_requests_id = fields.Many2one('res.users', string="User requesting", related='employee_id.user_id',
                                                store=True)
    user_manager_department_employee_requests_id = fields.Many2one(
        'res.users', readonly=True, string="User manager department collaborator requesting")
    amount = fields.Monetary(string="Amount", currency_field='currency_id', required=True, readonly=True, tracking=True)
    paid = fields.Boolean(string="Paid", readonly=True, tracking=True)
    company_id = fields.Many2one('res.company', string="Company", related='credit_id.company_id', readonly=True)
    currency_id = fields.Many2one('res.currency', string="Currency", related='credit_id.currency_id', readonly=True)
    credit_id = fields.Many2one('hr.credit', string="Credit", readonly=True, ondelete='cascade')
    state = fields.Selection(related='credit_id.state', string='Status', store=True, readonly=True)