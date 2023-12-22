# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class SalaryRuleProcess(models.Model):
    _name = 'hr.salary.rule.process'
    _description = 'Salary rule by process'
    _inherit = ['mail.thread']
    _rec_name = 'process'
    _order = "process"
    _sql_constraints = [
        ('code_unique',
         'UNIQUE(code)',
         _("Code must be unique.")),
    ]

    code = fields.Char(string='Code', required=True, help='', tracking=True)
    process = fields.Char(string='Process', required=True, help='', tracking=True)
    subprocess = fields.Char(string='Subprocess', required=True, help='', tracking=True)
    description = fields.Text(string='Description', help='', tracking=True)
    _MODE = [
        ('by_rules', _('By rules')),
        ('by_categories', _('By categories')),
    ]
    mode = fields.Selection(_MODE, string='Mode', default='by_rules', help='', required=True, tracking=True)
    salary_rule_code = fields.Char(string='Comma separated salary rule codes', help='', tracking=True)
    category_code = fields.Char(string='Comma separated category codes', help='', tracking=True)
    salary_rule_code_excluded = fields.Char(string='Comma separated salary rule codes excluded',
                                            help='', tracking=True)