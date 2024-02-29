# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class HrRuleInput(models.Model):
    _inherit = 'hr.rule.input'

    _TYPE = [
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('other_expense', 'Expense with beneficiary')]

    type = fields.Selection(_TYPE, string='Type', help='')