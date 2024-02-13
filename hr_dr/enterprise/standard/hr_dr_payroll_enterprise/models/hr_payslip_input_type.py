# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class PayslipInputType(models.Model):
    _inherit = 'hr.payslip.input.type'

    type = fields.Selection(
        [
            ('income', _('Income')),
            ('expense', _('Expense')),
            ('expense_with_beneficiary', _('Expense with beneficiary')),
            ('provision', _('Provision')),
            ('provision_crossing', _('Provision crossing'))
        ],
        string="Type", required=True, default="income")
    associated_rules = fields.Char(string='Associated rules')
    active = fields.Boolean(string="Active", default=True)