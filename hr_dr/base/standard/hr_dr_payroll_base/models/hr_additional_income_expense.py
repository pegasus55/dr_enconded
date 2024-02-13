# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AdditionalIncomeExpense(models.Model):
    _name = 'hr.additional.income.expense'
    _description = 'Additional income expense'
    _inherit = ['mail.thread']

    _TYPE = [
        ('income', _('Income')),
        ('expense', _('Expense')),
        ('expense_with_beneficiary', _('Expense with beneficiary'))
    ]

    rule_id = fields.Many2one('hr.salary.rule', string='Name', help='', tracking=True)
    amount = fields.Float(string='Value', help='', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Beneficiary', help='', tracking=True)
    type = fields.Selection(_TYPE, string='Type', help='', tracking=True)
    contract_id = fields.Many2one('hr.contract', string='Contract', help='', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, required=True,
                                  related='company_id.currency_id')