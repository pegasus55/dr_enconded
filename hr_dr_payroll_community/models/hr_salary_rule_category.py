# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class HrSalaryRuleCategory(models.Model):
    _name = 'hr.salary.rule.category'
    _inherit = ['hr.salary.rule.category', 'mail.thread']

    name = fields.Char(required=True, translate=True, tracking=True)
    code = fields.Char(required=True, tracking=True)
    parent_id = fields.Many2one('hr.salary.rule.category', string='Parent', tracking=True,
                                help="Linking a salary category to its parent is used only for the reporting purpose.")
    active = fields.Boolean(string='Active', default='True', help='', tracking=True)
