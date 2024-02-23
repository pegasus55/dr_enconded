# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class HrSalaryRuleCategory(models.Model):
    _name = 'hr.salary.rule.category'
    _inherit = ['hr.salary.rule.category', 'mail.thread']

    active = fields.Boolean(string='Active', default='True', help='', tracking=True)
